"""Combine the original Wordstep vocabulary with frequency-ranked TSL 1.2.

Preserves the original cards and progress identifiers; does not rewrite the original word list.
TSL / translated meanings / bilingual examples are attributed in the website footer.
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent

def key(s):
    return unicodedata.normalize('NFKC', s).casefold().strip()

BASE = json.loads((ROOT/'words.json').read_text(encoding='utf-8'))
TSL = json.loads((REPO/'working'/'tsl.json').read_text(encoding='utf-8'))

CATEGORY_MAP = {
    '辦公日常':'辦公室與工作',
    '一般專業':'跨情境高頻字彙',
    '營運管理':'公司與管理',
    '溝通互動':'人際溝通與情緒',
    '科技與技術支援':'科技與設備',
    '旅遊與交通':'商務旅行',
    '人力資源':'人事與招募',
    '採購與物流':'採購與訂單',
    '行銷與銷售':'行銷與廣告',
    '住宿與餐飲':'餐飲與服務',
    '物業與不動產':'房地產與設施',
    '金融與會計':'金融與銀行',
    '法務合規與安全':'法律與安全',
    '會議與簡報':'會議與商務溝通',
    '客戶服務':'銷售與客戶',
}
# Curated subject overrides prevent everyday nouns and school, nature, or leisure words
# from inheriting an unrelated "office"/"operations" topic from a general corpus.
TOPIC_WORDS = {
 '教育與學習':"""logical infer inference illogical explanatory comprehension contradict contradiction tutor textbook homework cumulative questionnaire usage scholarship graduate classmate faculty forum generalization guidance reflexive approximate amateur professionally literacy journalism repetition factual translation interpreter paraphrase restatement intonation trainee apprentice mentor instructor institute coursework seminar diploma certification certificate semester proficiency grade novice beginner memorize workbook journal pupil lecturer learn learner preliminary review reviewable editorial infographic""",
 '人際溝通與情緒':"""mister sincerely caller respondent announcer annoy unhappy spite pet congratulation polite interrupt patience appreciation apology congratulate enthusiastic dislike unsure verbal inappropriate amuse consent irritate rumor disappointment enjoyable repeatedly bye hesitant likewise uncomfortable enthusiastically messenger clap convey reluctant affirmative farewell loudly reassure reunion signify unpleasant assurance honestly needy someday suspicious whoever anyhow compliment desperate disgust gossip impatient indirect query willingness cheer considerate hesitation intently enthusiastic expressive upset discomfort smile emotional frustration flirt respond intuitive anxious""",
 '天氣與自然':"""cloudy sunny rainy windy chilly icy fog snowy sunshine humidity hurricane rainfall thunderstorm drought whale mosquito wildlife tropical seaside countryside earthquake ray pollute pollution environmentally habitat ecological planet sunset moon ocean balloon glacier breeze climate""",
 '活動與娛樂':"""picnic baseball soccer basketball violin drum orchestra jazz yoga jog runner skate skateboard volleyball hobby recreation amateur referee zoo cinema firefighter firework fireworks circus parade musical scenery contest contestant concert audience costume photography photographer artistic painter sculpture pottery thrill gymnasium dive enjoyable kayak performer actress movie soccer athlete athletic rehearsal""",
 '交通':"""bicycle airplane cruise captain hike cab cabin sidewalk jet ferry postcard brake excursion kilometer motorcycle jam aboard deck tow compartment sedan automotive underground escort vehicle van railroad highway commuter wheelchair commuter transport roadway traffic""",
 '商務旅行':"""sightsee hiker backpack getaway monument sunscreen explorer excursion sightseeing boarding purser tourism vacation passport luggage""",
 '健康與日常服務':"""dentist dental flu vitamin pill healthcare ward counselor checkup fatigue chronic nutrition dose prescribe diagnosis diagnose physician medical patient bacteria reflexive massage hygienic sunscreen headache fever clinic pharmacist athletic relief relieve sleepy fatigue""",
 '餐飲與服務':"""apple bean candy tomato pasta pizza steak ice cream juice soup salad sandwich snack hungry waitress recipe flavor catering culinary pie luncheon bake diner fry pan bakery barbecue hamburger popcorn flour pastry seafood butter cookbook tasty cheeseburger continental donut fork pepper tablecloth tuna homemade soda oatmeal"""
 ,
 '科技與設備':"""headphone cellphone laptop desktop e-book electrical cartridge developer delete directory packet mechanical automatic outdated faulty microscope programmer tech spam surf chemistry cookie compile tablet graphics browse physics telecommunication biology disconnect bug circuit generator refresh reliability transmission transmit activate slot adapter embed interactive retrieve stereo arc diagnostic disable electronically hacker modem outage satellite unplug calculator projector printer photovoltaic robotic digital copy smartphone email""",
 '人事與招募':"""supervisor recruiter internship intern termination layoff performance appraisal downsize unemployed prospective placement nomination dedication morale flextime senior junior personnel qualification applicant candidate employment compensation compensate payroll apprentice mentor recruiter assistant hire vacancy vacation supervisor promotion quit turnover dedication merit placement""",
 '金融與銀行':"""donation banker paycheck profitable incur statistics stockholder accumulate bankrupt economist downturn subtract fundraise teller collector yen economically bankruptcy overpay subsidize unpaid euro stockbroker recession rebate deductible deduction inflation appreciation credit withdraw account""",
 '物流與配送':"""freighter consignment postal postage carton shipment delivery dispatch freight expedite parcel mailer""",
 '採購與訂單':"""supermarket shopper cart affordable bargain grocery voucher garment durable costly equip inexpensive rack auction detach junk fabric commerce merchant lightweight footwear seller checkout seller purchase order return""",
 '房地產與設施':"""closet fountain bench residential realtor lawn suburb basement renter walkway architectural homeowner redecorate sewer condominium residence rug tile fixture mower carpenter gardener architect ladder ceiling hallway attic heating heater storeroom flooring walkway appliance refrigerator microwave dishwasher restroom storage bathroom sofa""",
 '法律與安全':"""prohibit exemption safely caution harmful attorney violation disagreement hazardous petition theft helmet sue evacuate extinguisher copyright forbid obligate paralegal trademark abide by-law hereby unauthorized violate suspicious cautions penalty penalize fireproof illegal identity""",
 '會議與商務溝通':"""presenter graph projector projection facilitate rehearse chairperson lecturer brainstorm diagram reconsider rehearsal videoconference infer contradictory respondent paraphrase minutes memorandum bulletin enclose spokesperson newsletter flyer proofread report correspondence microphone editor""",
 '行銷與廣告':"""mall jewelry innovative newsletter photographer subscribe exclusive photography seller popularity flyer showroom promotional actress mask celebrity colorful costume parade documentary elegant renown advertiser salesman booth vend cosmetic influential antique exotic dealership tempt desirable exclusively personalize prestigious artistic necklace pamphlet salespeople diamond acclaim""",
 '辦公室與工作':"""fax clerk publish enclose preview manual identification precede calendar rewrite drawer submission bulletin skim advisor ink administrative verify incomplete designate memorandum photocopier bookstore stack calculator completion omit urgent behalf booklet administrator finalize instruct overview boardroom classify revision badge graphic lengthy librarian merge unfamiliar rearrange reopen superior alert planner proofread deadline downstairs upstairs absent editorial layout simplify kit documentation reminder pad spreadsheet stapler toner locker stationery archive attire departmental letterhead incoming file folders clipboard keyboard pen paper binder stationary""",
 '日常生活與用品':"""cloth oval unreal glove vitamin basket vase gallon sunshine gum paperback stripe balloon cage fog gram wool wrinkle rubber skateboard plum pant scarf pajama garment umbrella appliance sweater sofa lamp wallet casual trash nap vacuum perfume soap purse nail sleeve clip apple sock sticker cord delicate outfit microwave cushion broom jeans raincoat wristwatch bulb bookcase cooler spray pillow blanket curtain mirror carpet countertop seat towel apparel lotion gift""",
 '常用描述與表達':"""sometime noon correctly clue compact inconvenience shortly aspect weekday commonly midnight lately thorough accurately optional definite thoroughly yearly cooperate distract hourly afterward strictly anytime meantime adjacent alternate considerably misplace unlimited irregular steadily expiration optimistic plausible unexpected adhere locally opt polish separately unnecessary accordingly beforehand excessive generic ongoing periodically consistently exceptional familiarize overlook preliminary smoothly acceptance appendix correction ideally insufficient noisy punctual shorten specially substantially tidy urgently absorb ample conform contrary energetic individually outlook timely await dependable disrupt internationally invaluable recur unusually cautious distraction enthusiasm evident fortunately imperative insert meaningful unused additionally collaboration consecutive discrepancy dull evenly formally poorly superb traditionally tremendous advisable circulate comfortably familiarity interfere partial probable prominent sharply terrific accuracy beneficial bound oblige occurrence partially permanently unreliable ordinary comparable drastically someday sometime somehow whatnot worthwhile familiar faraway mundane fluent correctly fluently roughly logically firstly secondly lastly sincerely distinctly nearly utterly likely early late often quickly indeed enough"""
}

CATEGORY_BY_WORD = {}
for topic, chunk in TOPIC_WORDS.items():
    for word in chunk.split():
        CATEGORY_BY_WORD[word] = topic
# Some words fit a narrower context than a corpus category. Keep clear user-facing themes.
CATEGORY_BY_WORD.update({
    'violin':'活動與娛樂','drum':'活動與娛樂',
    'counselor':'健康與日常服務','firework':'活動與娛樂',
    'soccer':'活動與娛樂','headphone':'科技與設備',
    'apple':'餐飲與服務','cloudy':'天氣與自然','violate':'法律與安全',
    'homework':'教育與學習','microscope':'科技與設備',
    'supervisor':'人事與招募','clerk':'辦公室與工作',
    'office':'辦公室與工作', 'checkout':'飯店與住宿',
    'e-book':'科技與設備','recreation':'活動與娛樂',
    'auto':'交通', 'playback':'科技與設備',
    'sunscreen':'商務旅行', 'bear':'天氣與自然',
    'pollute':'天氣與自然','hurricane':'天氣與自然',
    'unplug':'科技與設備','celebrity':'行銷與廣告',
    'résumé':'人事與招募','résume':'人事與招募',
    'painter':'活動與娛樂','jog':'活動與娛樂',
    'chef':'餐飲與服務','bookstore':'日常生活與用品',
    'ward':'健康與日常服務','marine':'天氣與自然',
    'spouse':'日常生活與用品','birthday':'活動與娛樂',
    'starter':'餐飲與服務','automotive':'製造與生產',
})
EXTRA_EXAMPLES = {
 'indoor': [('The indoor pool opens at seven.','室內游泳池七點開放。'),('Indoor activities are available on rainy days.','下雨天也有室內活動。')],
 'submission': [('The submission deadline is Friday.','提交截止日是星期五。')],
 'photocopier': [('The photocopier is out of paper.','影印機沒有紙了。')],
 'urgent': [('This is an urgent request.','這是一項緊急請求。')],
 'auto': [('The auto repair shop is nearby.','汽車修理廠就在附近。'),('The auto industry is changing quickly.','汽車產業正迅速改變。')],
 'appreciation': [('Thank you for your appreciation.','謝謝你的肯定。')],
 'distract': [('Please do not distract the driver.','請不要讓司機分心。')],
 'apology': [('She offered an apology for the delay.','她為延誤表達歉意。')],
 'automatic': [('The automatic door opens slowly.','自動門緩緩打開。')],
 'costly': [('The repair could be costly.','這項修理可能很昂貴。')],
 'translation': [('We need a translation of this document.','我們需要這份文件的譯本。')],
 'informal': [('This is an informal meeting.','這是一場非正式會議。')],
 'steadily': [('Sales have increased steadily.','銷售額一直穩定成長。')],
 'absent': [('Two employees were absent today.','今天有兩位員工缺席。')],
 'appraisal': [('Her performance appraisal is next week.','她的績效考核在下週。')],
 'apprentice': [('The apprentice learned from an experienced chef.','這位學徒向資深廚師學習。')],
 'bankrupt': [('The company went bankrupt last year.','這家公司去年破產了。')],
 'mentor': [('My mentor helped me prepare for the interview.','我的導師幫我準備面試。')],
 'renown': [('The restaurant has earned international renown.','這家餐廳享有國際聲譽。'),('Her renown grew after she won the award.','她獲獎後名聲更加響亮。')],
 'aboard': [('Please come aboard the train.','請上火車。')],
 'checkout': [('Hotel checkout is at eleven.','飯店退房時間是十一點。')],
 'firework': [('A firework lit up the sky.','一枚煙火照亮了天空。'),('The festival ended with a colorful firework display.','節慶以繽紛的煙火表演作結。')],
 'recreation': [('The park offers space for recreation.','這座公園提供休閒活動的空間。'),('Recreation is important for a balanced life.','休閒活動對平衡生活很重要。')],
 'influential': [('She is an influential business leader.','她是一位有影響力的商界領袖。')],
 'hesitant': [('He was hesitant to accept the offer.','他對接受這項提議有些猶豫。')],
 'cooler': [('Please put the drinks in the cooler.','請把飲料放進冷藏箱。'),('We brought a cooler to the picnic.','我們帶了一個冷藏箱去野餐。')],
 'disrupt': [('The storm could disrupt train service.','暴風雨可能中斷火車服務。')],
 'spray': [('Please do not spray water on the machine.','請不要在機器上噴水。')],
 'cautious': [('Be cautious when sharing personal data.','分享個人資料時要謹慎。')],
 'clap': [('Everyone began to clap after the speech.','演講結束後大家開始鼓掌。')],
 'counselor': [('The counselor can help students plan their careers.','輔導員可以協助學生規劃職涯。')],
 'affirmative': [('We received an affirmative response.','我們收到肯定的答覆。')],
 'violin': [('She plays the violin every evening.','她每天晚上拉小提琴。'),('The violin solo was beautiful.','小提琴獨奏非常優美。')],
 'archive': [('Please archive the old reports.','請將舊報告封存。')],
 'dose': [('Take only the prescribed dose.','請只服用處方指定的劑量。')],
 'drum': [('He plays the drum in the school band.','他在學校樂團打鼓。'),('The drum sounded loud in the hall.','鼓聲在大廳裡非常響亮。')],
 'layoff': [('The company announced a layoff.','公司宣布裁員。'),('The layoff affected several departments.','這次裁員影響多個部門。')],
 'pollute': [('Factories must not pollute the river.','工廠不可污染河川。')],
 'prominent': [('A prominent scientist will give the talk.','一位知名科學家將發表演講。')],
 'residence': [('Her residence is near the station.','她的住所靠近車站。')],
 'suspicious': [('Report any suspicious activity to security.','如發現可疑活動，請通知保全。')],
 'demolish': [('Workers will demolish the old building.','工人將拆除舊建築。')],
 'engagement': [('He has a prior engagement on Friday.','他星期五已有約。')],
 'nutrition': [('Good nutrition is important for children.','良好的營養對孩子很重要。')],
 'violate': [('Do not violate the safety rules.','不要違反安全規則。')]
}

def pick_category(row):
    term=key(row['word'])
    if term in CATEGORY_BY_WORD:
        return CATEGORY_BY_WORD[term]
    topic=CATEGORY_MAP.get(row.get('corpusCategory') or '', '跨情境高頻字彙')
    # Generic descriptive words in a broad corpus aren't necessarily office terms.
    if topic in ('辦公室與工作','公司與管理','跨情境高頻字彙'):
        part=row.get('pos','').split('.')[0]
        if part in ('adv','adj','conj','prep'):
            return '常用描述與表達'
    return topic

def clean_example(ex):
    return {'en':ex['en'].strip(),'zh':ex['zh'].strip()}

ranks={key(row['word']):int(row['rank']) for row in TSL}
assert len(TSL)==1250 and len(ranks)==1250
assert list(sorted(ranks.values()))==list(range(1,1251))
orig=set()
merged=[]
for word in BASE:
    term=key(word['word'])
    if term in orig:
        if term!='promotion': raise ValueError('Unexpected duplicate original word '+term)
        previous=next(w for w in merged if key(w['word'])==term)
        previous['meaning']='升遷；促銷／推廣'
        previous['phrase']='receive a promotion；sales promotion'
        previous['examples']=[previous['examples'][0],clean_example(word['examples'][0])]
        previous['categories']=['人事與招募','行銷與廣告']
        previous['aliases']=['w0206']
        continue
    orig.add(term)
    merged.append({**word,'base':True,'tslRank':ranks.get(term),'categories':[word['category']]})
assert len(merged)==999
existing={key(w['word']) for w in merged}
for row in TSL:
    term=key(row['word'])
    if term in existing:continue
    candidates=[clean_example(e) for e in row.get('examples',[]) if e.get('en') and e.get('zh')]
    authored=EXTRA_EXAMPLES.get(term,[])
    for en,zh in authored:
        if not any(e['en'].casefold()==en.casefold() for e in candidates):
            candidates.append({'en':en,'zh':zh})
        if len(candidates)>=2: break
    assert len(candidates)>=2, f'Missing original example or manual fallback: {row["word"]}'
    category=pick_category(row)
    assert category and category!='TSL'
    item=dict(word=row['word'],pos=row.get('pos') or '',meaning=row['meaning'],
        phrase=row.get('phrase') or '',category=category,categories=[category],
        id='tsl'+str(row['rank']).zfill(4),number=1000+row['rank'],
        examples=candidates[:2],tips=[],forms=row.get('forms') or [],base=False,
        tslRank=row['rank'],exampleSource='kknono668/toeic-vocab-tw or Wordstep authored')
    merged.append(item)
assert len(merged)==1969 and len({key(w['word']) for w in merged})==1969
assert sum(bool(w['base']) for w in merged)==999
assert sum(bool(w['tslRank']) for w in merged)==1250
assert sum(bool(w['tslRank'] and w['tslRank']<=500 and not w['base']) for w in merged)==300
assert all(len(w['examples'])==2 and all(e['en'].strip() and e['zh'].strip() for e in w['examples']) for w in merged)
assert len(Counter(w['category'] for w in merged))>=20
encoded=json.dumps(merged,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
template=(ROOT/'index.template.html').read_text(encoding='utf-8')
assert template.count('__WORDSTEP_DATA__')==1
out=REPO/'docs'/'index.html'
out.write_text(template.replace('__WORDSTEP_DATA__',encoded),encoding='utf-8')
(ROOT/'merged_1969.json').write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'tsl_1250.json').write_text(json.dumps(TSL,ensure_ascii=False,indent=2),encoding='utf-8')
print('Merged verified: 999 original spellings + 970 new TSL = 1969 cards; 300 priority additions')
print('Categories:',json.dumps(Counter(w['category'] for w in merged),ensure_ascii=False))
