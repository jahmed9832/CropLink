"""Bangla / English support. Request-e `Accept-Language: bn|en` header ba `?lang=bn|en` dile shob user-facing text oi bhashay ashe.
Machine-er jonno stable code (id, status, grade...) bodlay na - app logic code-er upor, dekhanor jonno text-er upor nirbhor korbe.
Bangla text-e shongkha Bangla digit (০-৯) hoy; JSON-er number field Latin digit-i thake."""
import contextvars
import os

LANG = contextvars.ContextVar("lang", default=os.getenv("DEFAULT_LANG", "bn"))
SUPPORTED = ("bn", "en")
_BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def detect(query_lang=None, accept_language=None):
    q = (query_lang or "").strip().lower()
    if q in SUPPORTED:
        return q
    for part in (accept_language or "").split(","):
        tag = part.split(";")[0].strip().lower()
        if tag.startswith("bn"):
            return "bn"
        if tag.startswith("en"):
            return "en"
    return os.getenv("DEFAULT_LANG", "bn")


def current_lang():
    return LANG.get()


def get_lang():
    return LANG.get()


CROP_NAMES = {
    "tomato": {"bn": "টমেটো", "en": "Tomato"}, "potato": {"bn": "আলু", "en": "Potato"},
    "onion": {"bn": "পেঁয়াজ", "en": "Onion"}, "brinjal": {"bn": "বেগুন", "en": "Brinjal"},
    "chili": {"bn": "মরিচ", "en": "Chili"}, "cabbage": {"bn": "বাঁধাকপি", "en": "Cabbage"},
    "rice": {"bn": "ধান/চাল", "en": "Rice"},
}
MARKET_NAMES = {
    "Dhaka": {"bn": "ঢাকা", "en": "Dhaka"}, "Chattogram": {"bn": "চট্টগ্রাম", "en": "Chattogram"},
    "Rajshahi": {"bn": "রাজশাহী", "en": "Rajshahi"}, "Bogura": {"bn": "বগুড়া", "en": "Bogura"},
    "Khulna": {"bn": "খুলনা", "en": "Khulna"},
}
GRADE_NAMES = {"A": {"bn": "গ্রেড এ", "en": "Grade A"}, "B": {"bn": "গ্রেড বি", "en": "Grade B"},
               "C": {"bn": "গ্রেড সি", "en": "Grade C"}}
STATUS_NAMES = {
    "open": {"bn": "খোলা", "en": "Open"}, "reserved": {"bn": "সংরক্ষিত", "en": "Reserved"},
    "sold": {"bn": "বিক্রিত", "en": "Sold"}, "withdrawn": {"bn": "তুলে নেওয়া", "en": "Withdrawn"},
    "filled": {"bn": "পূরণ হয়েছে", "en": "Filled"}, "closed": {"bn": "বন্ধ", "en": "Closed"},
    "confirmed": {"bn": "নিশ্চিত", "en": "Confirmed"}, "delivered": {"bn": "ডেলিভারি হয়েছে", "en": "Delivered"},
    "completed": {"bn": "সম্পন্ন", "en": "Completed"}, "cancelled": {"bn": "বাতিল", "en": "Cancelled"},
    "pending": {"bn": "অপেক্ষমাণ", "en": "Pending"}, "funded": {"bn": "টাকা জমা হয়েছে", "en": "Funded"},
    "released": {"bn": "টাকা ছাড় হয়েছে", "en": "Released"}, "refunded": {"bn": "ফেরত দেওয়া হয়েছে", "en": "Refunded"},
    "open_for_review": {"bn": "পর্যালোচনার অপেক্ষায়", "en": "Awaiting review"},
}


def _name(table, key, lang):
    lang = lang or LANG.get()
    e = table.get(key)
    return e[lang] if e else str(key)


def crop_name(c, lang=None): return _name(CROP_NAMES, c, lang)
def market_name(m, lang=None): return _name(MARKET_NAMES, m, lang)
def grade_name(g, lang=None): return _name(GRADE_NAMES, g, lang)
def status_name(s, lang=None): return _name(STATUS_NAMES, s, lang)


C = {
    # ---- decision engine
    "opt.sell_now": {"bn": "এখনই স্থানীয় বাজারে বিক্রি", "en": "Sell now at the local market"},
    "opt.wait": {"bn": "{days} দিন অপেক্ষা করে বিক্রি", "en": "Wait {days} days, then sell"},
    "opt.offer": {"bn": "ক্রেতার অফার: {name} ({price} টাকা/কেজি)", "en": "Buyer offer: {name} ({price} BDT/kg)"},
    "dec.best": {"bn": "সবচেয়ে ভালো বিকল্প: {label}। আনুমানিক নিট আয় {base} টাকা (সর্বনিম্ন {low}, সর্বোচ্চ {high})।",
                 "en": "Best option: {label}. Estimated net income {base} BDT (range {low} to {high})."},
    "dec.uplift": {"bn": "এখনই বিক্রির চেয়ে {pct}% বেশি আনুমানিক নিট আয়।", "en": "{pct}% more estimated net income than selling now."},
    "dec.safest": {"bn": "কম ঝুঁকি চাইলে '{label}' বেশি নিরাপদ (সবচেয়ে খারাপ ক্ষেত্রে {low} টাকা)।",
                   "en": "For lower risk, '{label}' is safer (worst case {low} BDT)."},
    "dec.wait_note": {"bn": "অপেক্ষার বিকল্পটি পূর্বাভাসের ওপর নির্ভরশীল। এটি নিশ্চিত নয়, দাম কমতেও পারে।",
                      "en": "Waiting depends on a forecast. It is not guaranteed and prices may fall."},
    "dec.disclaimer": {"bn": "এটি একটি অনুমান, নিশ্চিত আয় নয়। খরচ বা পরিমাণ ঠিক করে আবার হিসাব করুন।",
                       "en": "This is an estimate, not guaranteed income. Adjust costs or quantity and recalculate."},
    # ---- forecast / weather / grading
    "fc.note": {"bn": "এটি পূর্বাভাস, নিশ্চিত দাম নয়। সীমা (সর্বনিম্ন থেকে সর্বোচ্চ) দেখে সিদ্ধান্ত নিন।",
                "en": "This is a forecast, not a confirmed price. Decide using the range (low to high)."},
    "fc.short": {"bn": "কমপক্ষে {n} দিনের দামের তথ্য লাগবে।", "en": "At least {n} days of price data are needed."},
    "wx.default": {"bn": "আবহাওয়ার তথ্য পাওয়া যায়নি, তাই ডিফল্ট ৩০° সেলসিয়াস ধরা হয়েছে।",
                   "en": "Weather data is unavailable; assuming the default 30°C."},
    "grade.note": {"bn": "এটি প্রস্তাবিত গ্রেড, চূড়ান্ত নয়। আস্থা কম হলে হাতে-কলমে যাচাই করুন।",
                   "en": "This is a suggested grade, not final. If confidence is low, check it manually."},
    "grade.small": {"bn": "ছবিতে ফসল খুব ছোট বা দেখা যাচ্ছে না, কাছ থেকে ছবি তুলুন।",
                    "en": "The produce is too small or not visible in the photo; take the photo closer."},
    "grade.dark": {"bn": "ছবিটি খুব অন্ধকার।", "en": "The photo is too dark."},
    # ---- assistant
    "trend.up": {"bn": "বাড়তে পারে", "en": "may rise"}, "trend.down": {"bn": "কমতে পারে", "en": "may fall"},
    "trend.flat": {"bn": "মোটামুটি একই থাকতে পারে", "en": "may stay about the same"},
    "risk.low": {"bn": "কম", "en": "low"}, "risk.medium": {"bn": "মাঝারি", "en": "medium"}, "risk.high": {"bn": "বেশি", "en": "high"},
    "chat.help": {"bn": "আমি দাম, বিক্রির সঠিক সময়, নষ্ট হওয়ার ঝুঁকি ও দরদামে সাহায্য করতে পারি। যেমন বলুন: \"৫০০ কেজি টমেটো এখন বিক্রি করব নাকি অপেক্ষা করব?\"",
                  "en": "I can help with prices, the best time to sell, spoilage risk and negotiation. For example: \"Should I sell 500 kg of tomato now or wait?\""},
    "chat.ask_qty": {"bn": "কত কেজি {crop} আছে বলুন, তাহলে নিট আয়ের হিসাব করে দেব।",
                     "en": "How many kg of {crop} do you have? Then I can calculate the net income."},
    "chat.ask_qty_neg": {"bn": "কত কেজি {crop} আছে বলুন, তাহলে সর্বনিম্ন গ্রহণযোগ্য দাম হিসাব করে দেব।",
                         "en": "How many kg of {crop} do you have? Then I can calculate your minimum acceptable price."},
    "chat.price": {"bn": "{crop}-এর বর্তমান দাম প্রায় {price} টাকা/কেজি। ৭ দিন পরে দাম {trend}: আনুমানিক {low} থেকে {high} টাকা (সম্ভাব্য {base})। এটি পূর্বাভাস, নিশ্চিত দাম নয়।",
                   "en": "The current price of {crop} is about {price} BDT/kg. In 7 days it {trend}: roughly {low} to {high} BDT (likely {base}). This is a forecast, not a confirmed price."},
    "chat.loss": {"bn": "{crop} নষ্ট হওয়ার ঝুঁকি এখন {risk}। দ্রুত নিকটস্থ বাজারে বিক্রি করুন এবং ছায়ায় রাখুন।",
                  "en": "The spoilage risk for {crop} is {risk}. Sell at the nearest market soon and keep it in the shade."},
    "chat.sell": {"bn": "{qty} কেজি {crop}-এর জন্য সবচেয়ে ভালো বিকল্প: {label}। আনুমানিক নিট আয় {base} টাকা (সর্বনিম্ন {low}, সর্বোচ্চ {high})। এখনই বিক্রি করলে আনুমানিক {now} টাকা।",
                  "en": "For {qty} kg of {crop}, the best option is: {label}. Estimated net income is {base} BDT (range {low} to {high}). Selling now would give about {now} BDT."},
    "chat.sell_safe": {"bn": " কম ঝুঁকি চাইলে নিরাপদ বিকল্পটিও দেখুন।", "en": " For lower risk, also look at the safer option."},
    "chat.sell_tail": {"bn": " খরচ বা পরিমাণ ঠিক করে আবার হিসাব করতে পারেন।", "en": " You can adjust costs or quantity and recalculate."},
    "chat.neg": {"bn": "আপনার সর্বনিম্ন গ্রহণযোগ্য দাম প্রায় {min} টাকা/কেজি। ক্রেতার প্রস্তাব {offer} টাকা। ",
                 "en": "Your minimum acceptable price is about {min} BDT/kg. The buyer offered {offer} BDT. "},
    "chat.neg_accept": {"bn": "প্রস্তাবটি গ্রহণ করতে পারেন।", "en": "You can accept this offer."},
    "chat.neg_counter": {"bn": "{counter} টাকা পাল্টা প্রস্তাব দিতে পারেন।", "en": "You can counter with {counter} BDT."},
    # ---- negotiation
    "neg.disclaimer": {"bn": "খসড়া বার্তাটি কৃষক দেখে নিজে পাঠাবেন, সিস্টেম নিজে কিছু পাঠায় না। সর্বনিম্ন দাম ক্রেতাকে দেখাবেন না।",
                       "en": "The farmer reviews and sends the draft; the system never sends anything itself. Do not show your minimum price to the buyer."},
    "neg.floor": {"bn": "আপনার উৎপাদন খরচকে সর্বনিম্ন সীমা ধরা হয়েছে।", "en": "Your production cost was used as the price floor."},
    "neg.accept_draft": {"bn": "আপনার {offer} টাকা/কেজি প্রস্তাব আমার গ্রহণযোগ্য। {qty} কেজি {crop} ({grade}) দিতে পারব। ডেলিভারির সময় ও জায়গা নিশ্চিত করে জানান।",
                         "en": "Your offer of {offer} BDT/kg works for me for {qty} kg of {crop} ({grade}). Please confirm the delivery time and place."},
    "neg.counter_draft": {"bn": "আপনার প্রস্তাব {offer} টাকা/কেজি পেয়েছি। আমার {qty} কেজি {crop} ({grade}) আছে। বর্তমান বাজারদর ও মান অনুযায়ী {counter} টাকা/কেজি দরে দিতে পারব। এই দরে রাজি হলে জানান।",
                          "en": "Thank you for your offer of {offer} BDT/kg. I have {qty} kg of {crop} ({grade}). Based on current market rates and quality I can supply at {counter} BDT/kg. Please let me know if that works."},
    # ---- alerts
    "alert.spike": {"bn": "{market} বাজারে {crop}-এর দাম গত ৩০ দিনের গড়ের চেয়ে {pct}% বেশি। বিক্রির ভালো সময় হতে পারে।",
                    "en": "The {crop} price in {market} is {pct}% above its 30-day average. It may be a good time to sell."},
    "alert.drop": {"bn": "{market} বাজারে {crop}-এর দাম গত ৩০ দিনের গড়ের চেয়ে {pct}% কম। তাড়াহুড়ো করে বিক্রি না করাই ভালো, অন্য ক্রেতা দেখুন।",
                   "en": "The {crop} price in {market} is {pct}% below its 30-day average. Avoid rushing to sell; look at other buyers."},
    "alert.fc_up": {"bn": "{crop}-এর দাম {days} দিনে প্রায় {pct}% বাড়তে পারে (পূর্বাভাস, নিশ্চিত নয়)।",
                    "en": "The {crop} price may rise by about {pct}% in {days} days (forecast, not guaranteed)."},
    "alert.fc_down": {"bn": "{crop}-এর দাম {days} দিনে প্রায় {pct}% কমতে পারে (পূর্বাভাস, নিশ্চিত নয়)।",
                      "en": "The {crop} price may fall by about {pct}% in {days} days (forecast, not guaranteed)."},
    # ---- loss
    "loss.high": {"bn": "এখনই নিকটস্থ ক্রেতা বা বাজারে পাঠান। অপেক্ষা করলে ক্ষতি বাড়বে।", "en": "Send it to the nearest buyer or market now. Waiting will increase the loss."},
    "loss.heat": {"bn": "তাপমাত্রা বেশি। ছায়ায় রাখুন এবং রাতে বা ভোরে পরিবহন করুন।", "en": "It is hot. Keep it in the shade and transport at night or early morning."},
    "loss.deadline": {"bn": "ডেলিভারির সময়সীমার মধ্যে পৌঁছানো সম্ভব হবে না।", "en": "It will not arrive before the delivery deadline."},
    # ---- dispute
    "disp.weight": {"bn": "ওজনের পার্থক্য {pct}% (পরিবহনে ক্ষতি বা মাপার ভুল হতে পারে)", "en": "Weight difference of {pct}% (could be transit loss or a weighing error)"},
    "disp.grade": {"bn": "গ্রেড মেলেনি: {pre} থেকে {post} (দামের ব্যবধান {diff}%)", "en": "Grade mismatch: {pre} to {post} (price band difference {diff}%)"},
    "disp.deduction": {"bn": "ক্রেতা {pct}% মূল্য কর্তনের প্রস্তাব করেছেন", "en": "The buyer proposed a {pct}% price deduction"},
    "disp.lowconf": {"bn": "বিক্রির আগের গ্রেডিংয়ে আস্থা কম ছিল, ম্যানুয়াল পর্যালোচনা দরকার।", "en": "Pre-sale grading confidence was low; manual review is needed."},
    "disp.nophoto": {"bn": "বিক্রির আগের ছবি সংরক্ষিত নেই, প্রমাণ দুর্বল।", "en": "No pre-sale photo was recorded; the evidence is weak."},
    "disp.noreason": {"bn": "কর্তনের কারণ লেখা নেই।", "en": "No reason was given for the deduction."},
    "disp.statement": {"bn": "এটি পাশাপাশি তুলনামূলক প্রমাণ প্রতিবেদন। সিস্টেম কোনো পক্ষকে দোষী ঘোষণা করে না, মানুষ যাচাই করবে।",
                       "en": "This is a side-by-side evidence report. The system does not declare either party at fault; a person will review it."},
    # ---- reliability
    "rel.limited": {"bn": "যাচাইকৃত লেনদেন ৫টির কম, তাই স্কোর দেওয়া হয়নি (খারাপ হিসেবে ধরা হয়নি)।", "en": "Fewer than 5 verified transactions, so no score was given (this is not treated as poor)."},
    "rel.ontime": {"bn": "{ok}/{n}টি অর্ডারে সময়মতো পেমেন্ট", "en": "On-time payment in {ok} of {n} orders"},
    "rel.cancel": {"bn": "ক্রেতার পক্ষ থেকে বাতিল {n}টি", "en": "{n} cancellation(s) by the buyer"},
    "rel.dispute": {"bn": "ক্রেতার বিরুদ্ধে নথিভুক্ত বিরোধ {n}টি", "en": "{n} documented dispute(s) resolved against the buyer"},
    # ---- pooling / demand
    "pool.crop": {"bn": "ফসল মেলেনি", "en": "Crop does not match"}, "pool.grade": {"bn": "গ্রেড কম", "en": "Grade is too low"},
    "pool.dist": {"bn": "দূরত্ব বেশি", "en": "Too far"}, "pool.deadline": {"bn": "ফসল তোলার তারিখ সময়সীমার পরে", "en": "Harvest date is after the deadline"},
    "pool.notopen": {"bn": "লট খোলা নেই", "en": "The lot is not open"},
    "pool.window": {"bn": "ফসল তোলার তারিখ {days} দিনের সীমার বাইরে", "en": "Harvest date is outside the {days}-day window"},
    "pool.note": {"bn": "প্রতিটি লট আলাদাভাবে ট্র্যাক হয়; একজনের সমস্যা অন্যদের বরাদ্দে নীরবে প্রভাব ফেলে না।",
                  "en": "Each lot is tracked separately; one participant's issue does not silently affect the others' allocations."},
    "demand.short": {"bn": "এটি পূর্বাভাস, নিশ্চিত অর্ডার নয়। কমপক্ষে ৮ সপ্তাহের সম্পন্ন অর্ডারের ইতিহাস লাগবে।",
                     "en": "This is a prediction, not a confirmed order. At least 8 weeks of completed-order history is needed."},
    "demand.ok": {"bn": "এটি পূর্বাভাস, নিশ্চিত অর্ডার নয়।", "en": "This is a prediction, not a confirmed order."},
    # ---- labels for codes (reliability, price fairness)
    "rel.label.limited_history": {"bn": "সীমিত ইতিহাস", "en": "Limited history"},
    "rel.label.high": {"bn": "উচ্চ নির্ভরযোগ্যতা", "en": "High reliability"},
    "rel.label.medium": {"bn": "মাঝারি নির্ভরযোগ্যতা", "en": "Medium reliability"},
    "rel.label.low": {"bn": "কম নির্ভরযোগ্যতা", "en": "Low reliability"},
    "fair.below_fair": {"bn": "বাজারদরের চেয়ে কম", "en": "Below market rate"},
    "fair.fair": {"bn": "ন্যায্য দাম", "en": "Fair price"},
    "fair.above_fair": {"bn": "বাজারদরের চেয়ে বেশি", "en": "Above market rate"},
    # ---- misc notes
    "passport.note": {"bn": "রপ্তানির জন্য অতিরিক্ত যাচাই লাগবে।", "en": "Additional validation is required for export compliance."},
    "dash.gross": {"bn": "মোট বিক্রি খরচ ও কমিশনের আগের হিসাব।", "en": "Gross sales are before costs and commission."},
    # ---- errors (HTTP detail)
    "err.apikey": {"bn": "X-API-Key ভুল বা নেই।", "en": "Invalid or missing X-API-Key."},
    "err.login": {"bn": "অনুগ্রহ করে লগইন করুন।", "en": "Please log in."},
    "err.token": {"bn": "টোকেন ভুল বা মেয়াদ শেষ, আবার লগইন করুন।", "en": "Invalid or expired token; please log in again."},
    "err.forbid": {"bn": "এটি করার অনুমতি আপনার নেই।", "en": "You are not allowed to do this."},
    "err.owner": {"bn": "এই তথ্য অন্য ব্যবহারকারীর, আপনি পরিবর্তন করতে পারবেন না।", "en": "This belongs to another user; you cannot change it."},
    "err.party": {"bn": "আপনি এই অর্ডারের সাথে যুক্ত নন।", "en": "You are not part of this order."},
    "err.role": {"bn": "শুধু {roles} এটি করতে পারেন।", "en": "Only {roles} can do this."},
    "err.notfound": {"bn": "{what} পাওয়া যায়নি।", "en": "{what} not found."},
    "err.crop": {"bn": "ফসল অবশ্যই এগুলোর একটি হতে হবে: {list}", "en": "Crop must be one of: {list}"},
    "err.market": {"bn": "বাজার অবশ্যই এগুলোর একটি হতে হবে: {list}", "en": "Market must be one of: {list}"},
    "err.role_value": {"bn": "ভূমিকা হতে হবে farmer অথবা buyer।", "en": "Role must be farmer or buyer."},
    "err.phone_exists": {"bn": "এই ফোন নম্বর দিয়ে আগেই অ্যাকাউন্ট খোলা আছে।", "en": "An account with this phone number already exists."},
    "err.login_bad": {"bn": "ফোন নম্বর বা পাসওয়ার্ড ভুল।", "en": "Wrong phone number or password."},
    "err.admin_edit": {"bn": "অ্যাডমিনের প্রোফাইল এখান থেকে বদলানো যায় না।", "en": "The admin profile cannot be edited here."},
    "err.img_big": {"bn": "ছবির আকার ৮ এমবির বেশি।", "en": "The image is larger than 8 MB."},
    "err.img_bad": {"bn": "ছবিটি পড়া গেল না, jpg বা png দিন।", "en": "Could not read the image; please send a jpg or png."},
    "err.photo_big": {"bn": "ছবির ডেটা অনেক বড়; ছোট থাম্বনেইল বা photo_url দিন।", "en": "The photo data is too large; send a small thumbnail or a photo_url."},
    "err.qty": {"bn": "পরিমাণ ০-এর বেশি হতে হবে।", "en": "Quantity must be greater than 0."},
    "err.lot_closed": {"bn": "এই লট আর খোলা নেই (অবস্থা: {status})।", "en": "This lot is no longer open (status: {status})."},
    "err.lot_over": {"bn": "লটের পরিমাণের চেয়ে বেশি বরাদ্দ দেওয়া যায় না।", "en": "Allocation cannot exceed the lot quantity."},
    "err.demand_closed": {"bn": "এই চাহিদা আর খোলা নেই (অবস্থা: {status})।", "en": "This demand is no longer open (status: {status})."},
    "err.pay_action": {"bn": "action হতে হবে: fund, release, refund বা cancel।", "en": "action must be one of: fund, release, refund, cancel."},
    "err.pay_state": {"bn": "পেমেন্টের অবস্থা '{status}' থাকলে '{action}' করা যায় না।", "en": "Cannot '{action}' while the payment status is '{status}'."},
    "err.offer_price": {"bn": "প্রতিটি অফারে price_per_kg দিতে হবে।", "en": "Every offer needs price_per_kg."},
}

ENT = {  # need(doc, what) -er "what"
    "Farmer": {"bn": "কৃষক", "en": "Farmer"}, "Buyer": {"bn": "ক্রেতা", "en": "Buyer"}, "Lot": {"bn": "লট", "en": "Lot"},
    "Demand": {"bn": "চাহিদা", "en": "Demand"}, "Batch": {"bn": "ব্যাচ", "en": "Batch"}, "Order": {"bn": "অর্ডার", "en": "Order"},
    "Evidence report": {"bn": "প্রমাণ প্রতিবেদন (আগে ডেলিভারি রেকর্ড করুন)", "en": "Evidence report (record the delivery first)"},
}


def t(key, lang=None, **kw):
    lang = lang or LANG.get()
    entry = C[key]
    text = entry.get(lang) or entry["en"]
    if "what" in kw and kw["what"] in ENT:
        kw["what"] = ENT[kw["what"]][lang]
    text = text.format(**kw) if kw else text
    return text.translate(_BN_DIGITS) if lang == "bn" else text
