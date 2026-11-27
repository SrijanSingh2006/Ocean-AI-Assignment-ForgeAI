"""Source-aligned localizations for the fictional People Operations policies.

The English text is the lookup key. Unseen or edited text goes through the
configured translator. Only the answer is localized; source quotes remain intact.
"""

from .multilingual import comparable_symbols


PASSAGES = (
    (
        "Permanent shore employees receive 22 paid annual leave days per calendar year. Carryover is capped at five days and expires on 31 March of the next year.",
        "तट पर कार्यरत स्थायी कर्मचारियों को हर कैलेंडर वर्ष में 22 दिन का सवेतन वार्षिक अवकाश मिलता है। अधिकतम पाँच दिन का बचा हुआ अवकाश अगले वर्ष में ले जाया जा सकता है। यह अवकाश अगले वर्ष की 31 मार्च को समाप्त हो जाता है।",
        "கரைப் பணிகளில் உள்ள நிரந்தர ஊழியர்களுக்கு ஒவ்வொரு காலண்டர் ஆண்டும் ஊதியத்துடன் 22 நாட்கள் வருடாந்திர விடுப்பு கிடைக்கும். பயன்படுத்தாத விடுப்பில் அதிகபட்சம் ஐந்து நாட்களை அடுத்த ஆண்டுக்கு மாற்றலாம். அந்த விடுப்பு அடுத்த ஆண்டு மார்ச் 31 அன்று காலாவதியாகும்.",
    ),
    (
        "Permanent shore employees receive 25 paid annual leave days per calendar year. Carryover is capped at five days and expires on 31 March of the next year.",
        "तट पर कार्यरत स्थायी कर्मचारियों को हर कैलेंडर वर्ष में 25 दिन का सवेतन वार्षिक अवकाश मिलता है। अधिकतम पाँच दिन का बचा हुआ अवकाश अगले वर्ष में ले जाया जा सकता है। यह अवकाश अगले वर्ष की 31 मार्च को समाप्त हो जाता है।",
        "கரைப் பணிகளில் உள்ள நிரந்தர ஊழியர்களுக்கு ஒவ்வொரு காலண்டர் ஆண்டும் ஊதியத்துடன் 25 நாட்கள் வருடாந்திர விடுப்பு கிடைக்கும். பயன்படுத்தாத விடுப்பில் அதிகபட்சம் ஐந்து நாட்களை அடுத்த ஆண்டுக்கு மாற்றலாம். அந்த விடுப்பு அடுத்த ஆண்டு மார்ச் 31 அன்று காலாவதியாகும்.",
    ),
    (
        "Employees in eligible shore roles may work remotely up to two days each week. The team lead approves the days in the shared team calendar.",
        "तट पर पात्र भूमिकाओं में काम करने वाले कर्मचारी हर सप्ताह अधिकतम दो दिन दूरस्थ रूप से काम कर सकते हैं। टीम प्रमुख साझा टीम कैलेंडर में उन दिनों को मंज़ूरी देते हैं।",
        "கரைப் பணிகளில் தகுதியுள்ள ஊழியர்கள் வாரத்துக்கு அதிகபட்சம் இரண்டு நாட்கள் தொலைவிலிருந்து பணிபுரியலாம். குழுத் தலைவர் பகிரப்பட்ட குழு நாள்காட்டியில் அந்த நாட்களுக்கு ஒப்புதல் அளிப்பார்.",
    ),
    (
        "Notify your line manager before 09:30 local time on the first day of sickness. A medical certificate is required after three consecutive working days.",
        "बीमारी के पहले दिन स्थानीय समयानुसार 09:30 बजे से पहले अपने प्रत्यक्ष प्रबंधक को सूचित करें। लगातार तीन कार्यदिवसों के बाद चिकित्सा प्रमाणपत्र देना अनिवार्य है।",
        "உடல்நலக்குறைவின் முதல் நாளில் உள்ளூர் நேரப்படி 09:30 மணிக்கு முன்பாக உங்கள் நேரடி மேலாளருக்குத் தெரிவிக்கவும். தொடர்ச்சியான மூன்று வேலை நாட்களுக்குப் பிறகு மருத்துவச் சான்றிதழ் கட்டாயம்.",
    ),
    (
        "Submit ordinary leave requests in the PeopleHub portal at least ten working days before departure. A line manager must approve the request before booking travel.",
        "सामान्य अवकाश का आवेदन प्रस्थान से कम से कम दस कार्यदिवस पहले PeopleHub पोर्टल में जमा करें। यात्रा की बुकिंग से पहले प्रत्यक्ष प्रबंधक की मंज़ूरी लेना अनिवार्य है।",
        "புறப்படுவதற்கு குறைந்தது பத்து வேலை நாட்களுக்கு முன் வழக்கமான விடுப்பு விண்ணப்பத்தை PeopleHub தளத்தில் சமர்ப்பிக்கவும். பயண முன்பதிவுக்கு முன் நேரடி மேலாளர் விண்ணப்பத்துக்கு ஒப்புதல் அளிக்க வேண்டும்.",
    ),
    (
        "Submit travel reimbursements in the expense portal within 30 calendar days of returning. Attach itemized receipts for every claimed expense.",
        "लौटने के 30 कैलेंडर दिनों के भीतर व्यय पोर्टल में यात्रा व्यय की प्रतिपूर्ति का दावा जमा करें। जिस भी खर्च का दावा करें, उसकी मदवार रसीद संलग्न करें।",
        "பயணத்திலிருந்து திரும்பிய 30 காலண்டர் நாட்களுக்குள் செலவுத் தளத்தில் பயணச் செலவுத் திருப்பீட்டுக்கான கோரிக்கையைச் சமர்ப்பிக்கவும். கோரும் ஒவ்வொரு செலவுக்கும் பொருள்வாரியான ரசீதை இணைக்கவும்.",
    ),
    (
        "The standard overnight hotel cap is EUR 145 per night before local taxes. A regional director may approve a higher amount before travel.",
        "स्थानीय करों से पहले होटल में रात्रि ठहराव की सामान्य सीमा EUR 145 प्रति रात है। क्षेत्रीय निदेशक यात्रा से पहले ज़्यादा राशि को मंज़ूरी दे सकते हैं।",
        "உள்ளூர் வரிகளுக்கு முன், ஓர் இரவு ஹோட்டல் தங்கலுக்கான வழக்கமான உச்சவரம்பு EUR 145. பயணத்திற்கு முன் மண்டல இயக்குநர் அதிக தொகைக்கு ஒப்புதல் அளிக்கலாம்.",
    ),
    (
        "Training allowance Shore employees may request up to EUR 350 annually for accredited courses. Submit the request in PeopleHub before paying the course provider.",
        "प्रशिक्षण भत्ता। तट पर कार्यरत कर्मचारी मान्यता प्राप्त पाठ्यक्रमों के लिए सालाना अधिकतम EUR 350 का अनुरोध कर सकते हैं। पाठ्यक्रम प्रदाता को भुगतान करने से पहले PeopleHub में अनुरोध जमा करें।",
        "பயிற்சி உதவித்தொகை. கரைப் பணிகளில் உள்ள ஊழியர்கள் அங்கீகாரம் பெற்ற படிப்புகளுக்கு ஆண்டுக்கு அதிகபட்சம் EUR 350 கோரலாம். படிப்பை வழங்கும் நிறுவனத்துக்குப் பணம் செலுத்துவதற்கு முன் PeopleHub தளத்தில் விண்ணப்பிக்கவும்.",
    ),
)

_BY_TEXT = {
    text: {"en": english, "hi": hindi, "ta": tamil}
    for english, hindi, tamil in PASSAGES
    for text in (english, hindi, tamil)
}


def localize_evidence(result, target):
    quotes = [citation["quote"] for citation in result["citations"]]
    if not quotes or result["answer"] != "\n\n".join(quotes):
        return None
    localized = []
    for quote in quotes:
        translation = _BY_TEXT.get(quote, {}).get(target)
        if not translation or comparable_symbols(quote) != comparable_symbols(translation):
            return None
        localized.append(translation)
    return "\n\n".join(localized)
