"""Optional CPU adapters for operator-installed NLLB and multilingual E5 weights."""

from functools import lru_cache
from pathlib import Path
import re
import time

from .embeddings import Embeddings
from .model import LatencyBudgetExceeded


CODES = {"en": "eng_Latn", "hi": "hin_Deva", "ta": "tam_Taml"}
GUARDS = (
    r"\b(?:not|no|never|prohibited|cannot|can't)\b",
    r"\b(?:except|unless|excluding|exception)\b",
    r"\b(?:only|solely|exclusively)\b",
    r"\b(?:before|prior to|earlier than)\b",
    r"\b(?:after|following|later than)\b",
    r"\b(?:maximum|at most|up to|no more than)\b",
    r"\b(?:minimum|at least|no less than)\b",
    r"\b(?:must|required|mandatory|shall)\b",
)


@lru_cache(maxsize=2)
def nllb_model(folder):
    import ctranslate2
    import sentencepiece

    return (
        ctranslate2.Translator(str(folder), device="cpu", compute_type="int8", intra_threads=2),
        sentencepiece.SentencePieceProcessor(model_file=str(folder / "sentencepiece.bpe.model")),
    )


class LocalTranslation:
    name = "nllb-200-distilled-600m"

    def __init__(self, folder, embeddings=None):
        self.folder = Path(folder)
        self.embeddings = embeddings
        self.deadline = None

    def ask(self, stage, payload, max_tokens=400):
        from .multilingual import LANGUAGES, detect_language

        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise LatencyBudgetExceeded("The multilingual evaluation budget expired.")
        text = payload["text"]
        source = detect_language(text).split("-")[0]
        target = next((code for code, label in LANGUAGES.items() if label == payload["target_language"]), None)
        if stage != "translate" or not target:
            return {}
        if source == target:
            return {"text": text}
        try:
            model, tokenizer = nllb_model(self.folder)
            pieces = tokenizer.encode(text, out_type=str)
            if len(pieces) > 450:
                return {}
            result = model.translate_batch(
                [[CODES[source], *pieces, "</s>"]], target_prefix=[[CODES[target]]],
                beam_size=4, max_decoding_length=max_tokens,
            )[0].hypotheses[0]
            return {"text": tokenizer.decode(result[1:])}
        except (OSError, RuntimeError, ValueError, ImportError):
            return {}

    def equivalent(self, original, roundtrip):
        if not self.embeddings:
            return False
        flags = lambda text: [bool(re.search(pattern, text, re.I)) for pattern in GUARDS]
        if flags(original) != flags(roundtrip):
            return False
        terms = lambda text: set(re.findall(r"[^\W_]+", text.casefold()))
        left, right = terms(original), terms(roundtrip)
        if not left or len(left & right) / len(left) < 0.60:
            return False
        try:
            return self.embeddings.similarity(original, roundtrip) >= 0.91
        except (OSError, ValueError, RuntimeError):
            return False


class LocalEmbeddings(Embeddings):
    """E5 pooling and normalization for a local standard BERT ONNX export."""

    def __init__(self, folder):
        import onnxruntime
        from tokenizers import Tokenizer

        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = onnxruntime.InferenceSession(str(folder / "model.onnx"), options, providers=["CPUExecutionProvider"])
        self.inputs = {item.name for item in self.session.get_inputs()}
        self.tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=256)
        self.tokenizer.enable_padding(pad_id=1, pad_token="<pad>")

    @lru_cache(maxsize=20)
    def vectors(self, texts):
        import numpy as np

        result = []
        for start in range(0, len(texts), 12):
            items = self.tokenizer.encode_batch(list(texts[start:start + 12]))
            mask = np.array([item.attention_mask for item in items], dtype=np.int64)
            data = {"input_ids": np.array([item.ids for item in items], dtype=np.int64),
                    "attention_mask": mask, "token_type_ids": np.zeros_like(mask)}
            hidden = self.session.run(None, {key: data[key] for key in self.inputs})[0]
            pooled = (hidden * mask[..., None]).sum(axis=1) / mask.sum(axis=1)[:, None]
            norms = np.linalg.norm(pooled, axis=1, keepdims=True)
            if not np.isfinite(pooled).all() or not (norms > 0).all():
                raise ValueError("The local embedding result is invalid.")
            result.extend((pooled / norms).tolist())
        return result

    def encode(self, texts):
        return self.vectors(("query: " + texts[0],)) + self.vectors(tuple("passage: " + text for text in texts[1:]))

    def similarity(self, left, right):
        a, b = self.vectors(("passage: " + left, "passage: " + right))
        return sum(x * y for x, y in zip(a, b))


@lru_cache(maxsize=2)
def local_embeddings(folder):
    try:
        return LocalEmbeddings(Path(folder))
    except (OSError, ImportError, RuntimeError, ValueError):
        return None
