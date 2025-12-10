import os
import json
import datetime
import traceback
import logging
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import re
from openai import OpenAI
from bs4 import BeautifulSoup
import random
import string
from pytz import timezone as pytz_timezone
from datetime import datetime as dt

# === Setup ===
load_dotenv()
app = Flask(__name__)

# --- Config ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PORT = int(os.getenv("PORT", 5000))

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# --- Business Hours Configuration (IST) ---
BUSINESS_TIMEZONE = "Asia/Kolkata"
BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 18
BUSINESS_DAYS = [0, 1, 2, 3, 4, 5]

# --- OpenAI Client ---
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Logging ---
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()
LEAD_LOG = "logs/leads.jsonl"

# --- Country & Currency Data ---
COUNTRY_CURRENCY_MAP = {
    "Afghanistan": {"currency_code": "AFN", "currency": "Afghan Afghani", "timezone": "Asia/Kabul"},
    "Albania": {"currency_code": "ALL", "currency": "Albanian Lek", "timezone": "Europe/Tirane"},
    "Algeria": {"currency_code": "DZD", "currency": "Algerian Dinar", "timezone": "Africa/Algiers"},
    "Argentina": {"currency_code": "ARS", "currency": "Argentine Peso", "timezone": "America/Argentina/Buenos_Aires"},
    "Armenia": {"currency_code": "AMD", "currency": "Armenian Dram", "timezone": "Asia/Yerevan"},
    "Australia": {"currency_code": "AUD", "currency": "Australian Dollar", "timezone": "Australia/Sydney"},
    "Austria": {"currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Vienna"},
    "Azerbaijan": {"currency_code": "AZN", "currency": "Azerbaijani Manat", "timezone": "Asia/Baku"},
    "Bahrain": {"currency_code": "BHD", "currency": "Bahraini Dinar", "timezone": "Asia/Bahrain"},
    "Bangladesh": {"currency_code": "BDT", "currency": "Bangladeshi Taka", "timezone": "Asia/Dhaka"},
    "Belgium": {"currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Brussels"},
    "Brazil": {"currency_code": "BRL", "currency": "Brazilian Real", "timezone": "America/Sao_Paulo"},
    "Canada": {"currency_code": "CAD", "currency": "Canadian Dollar", "timezone": "America/Toronto"},
    "China": {"currency_code": "CNY", "currency": "Chinese Yuan", "timezone": "Asia/Shanghai"},
    "Denmark": {"currency_code": "DKK", "currency": "Danish Krone", "timezone": "Europe/Copenhagen"},
    "Egypt": {"currency_code": "EGP", "currency": "Egyptian Pound", "timezone": "Africa/Cairo"},
    "France": {"currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Paris"},
    "Germany": {"currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Berlin"},
    "Hong Kong": {"currency_code": "HKD", "currency": "Hong Kong Dollar", "timezone": "Asia/Hong_Kong"},
    "India": {"currency_code": "INR", "currency": "Indian Rupee", "timezone": "Asia/Kolkata"},
    "Indonesia": {"currency_code": "IDR", "currency": "Indonesian Rupiah", "timezone": "Asia/Jakarta"},
    "Iran": {"currency_code": "IRR", "currency": "Iranian Rial", "timezone": "Asia/Tehran"},
    "Iraq": {"currency_code": "IQD", "currency": "Iraqi Dinar", "timezone": "Asia/Baghdad"},
    "Ireland": {"currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Dublin"},
    "Israel": {"currency_code": "ILS", "currency": "Israeli New Shekel", "timezone": "Asia/Jerusalem"},
    "Italy": {"currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Rome"},
    "Japan": {"currency_code": "JPY", "currency": "Japanese Yen", "timezone": "Asia/Tokyo"},
    "Jordan": {"currency_code": "JOD", "currency": "Jordanian Dinar", "timezone": "Asia/Amman"},
    "Kenya": {"currency_code": "KES", "currency": "Kenyan Shilling", "timezone": "Africa/Nairobi"},
    "Kuwait": {"currency_code": "KWD", "currency": "Kuwaiti Dinar", "timezone": "Asia/Kuwait"},
    "Malaysia": {"currency_code": "MYR", "currency": "Malaysian Ringgit", "timezone": "Asia/Kuala_Lumpur"},
    "Mexico": {"currency_code": "MXN", "currency": "Mexican Peso", "timezone": "America/Mexico_City"},
    "Nepal": {"currency_code": "NPR", "currency": "Nepalese Rupee", "timezone": "Asia/Kathmandu"},
    "Netherlands": {"currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Amsterdam"},
    "New Zealand": {"currency_code": "NZD", "currency": "New Zealand Dollar", "timezone": "Pacific/Auckland"},
    "Nigeria": {"currency_code": "NGN", "currency": "Nigerian Naira", "timezone": "Africa/Lagos"},
    "Norway": {"currency_code": "NOK", "currency": "Norwegian Krone", "timezone": "Europe/Oslo"},
    "Oman": {"currency_code": "OMR", "currency": "Omani Rial", "timezone": "Asia/Muscat"},
    "Pakistan": {"currency_code": "PKR", "currency": "Pakistani Rupee", "timezone": "Asia/Karachi"},
    "Philippines": {"currency_code": "PHP", "currency": "Philippine Peso", "timezone": "Asia/Manila"},
    "Poland": {"currency_code": "PLN", "currency": "Polish Zloty", "timezone": "Europe/Warsaw"},
    "Portugal": {"currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Lisbon"},
    "Qatar": {"currency_code": "QAR", "currency": "Qatari Riyal", "timezone": "Asia/Qatar"},
    "Russia": {"currency_code": "RUB", "currency": "Russian Ruble", "timezone": "Europe/Moscow"},
    "Saudi Arabia": {"currency_code": "SAR", "currency": "Saudi Riyal", "timezone": "Asia/Riyadh"},
    "Singapore": {"currency_code": "SGD", "currency": "Singapore Dollar", "timezone": "Asia/Singapore"},
    "South Africa": {"currency_code": "ZAR", "currency": "South African Rand", "timezone": "Africa/Johannesburg"},
    "South Korea": {"currency_code": "KRW", "currency": "South Korean Won", "timezone": "Asia/Seoul"},
    "Spain": {"currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Madrid"},
    "Sri Lanka": {"currency_code": "LKR", "currency": "Sri Lankan Rupee", "timezone": "Asia/Colombo"},
    "Sweden": {"currency_code": "SEK", "currency": "Swedish Krona", "timezone": "Europe/Stockholm"},
    "Switzerland": {"currency_code": "CHF", "currency": "Swiss Franc", "timezone": "Europe/Zurich"},
    "Taiwan": {"currency_code": "TWD", "currency": "New Taiwan Dollar", "timezone": "Asia/Taipei"},
    "Thailand": {"currency_code": "THB", "currency": "Thai Baht", "timezone": "Asia/Bangkok"},
    "Turkey": {"currency_code": "TRY", "currency": "Turkish Lira", "timezone": "Europe/Istanbul"},
    "Ukraine": {"currency_code": "UAH", "currency": "Ukrainian Hryvnia", "timezone": "Europe/Kiev"},
    "United Arab Emirates": {"currency_code": "AED", "currency": "UAE Dirham", "timezone": "Asia/Dubai"},
    "United Kingdom": {"currency_code": "GBP", "currency": "Pound Sterling", "timezone": "Europe/London"},
    "United States": {"currency_code": "USD", "currency": "United States Dollar", "timezone": "America/New_York"},
    "Vietnam": {"currency_code": "VND", "currency": "Vietnamese Dong", "timezone": "Asia/Ho_Chi_Minh"},
}

# --- Product Pricing Database ---
PRODUCT_PRICES = {
    "ALEXANDRITE": {"min_price_per_carat": 60000, "max_price_per_carat": "60000+", "notes": "Indian origin: 25000-350000"},
    "ALEXANDRITE CATS EYE": {"min_price_per_carat": 60000, "max_price_per_carat": "60000+"},
    "AMETHYST": {"min_price_per_carat": 380, "max_price_per_carat": 13000},
    "AUSTRALIAN OPAL": {"min_price_per_carat": 150, "max_price_per_carat": 7000},
    "BLUE SAPPHIRE": {"min_price_per_carat": 25000, "max_price_per_carat": "50000+", "notes": "Kashmir/Burmese origins command premium"},
    "BLUE SAPPHIRE (NEELAM)": {"min_price_per_carat": 25000, "max_price_per_carat": "50000+"},
    "COLOMBIAN EMERALD": {"min_price_per_carat": 1155277, "max_price_per_carat": 1155277},
    "CULTURED PEARLS": {"min_price_per_carat": 1000, "max_price_per_carat": "20000+"},
    "EMERALD": {"min_price_per_carat": 1000, "max_price_per_carat": 437000, "notes": "Persian Emerald command higher price"},
    "EMERALD (PANNA)": {"min_price_per_carat": 1000, "max_price_per_carat": 437000},
    "OPAL": {"min_price_per_carat": 150, "max_price_per_carat": 7000},
    "PERIDOT": {"min_price_per_carat": 664, "max_price_per_carat": 29216},
    "RED CORAL": {"min_price_per_carat": 1000, "max_price_per_carat": 5000},
    "RED CORAL (MOONGA)": {"min_price_per_carat": 1000, "max_price_per_carat": 5000},
    "RUBY": {"min_price_per_carat": 50000, "max_price_per_carat": 500000},
    "RUBY (MANIK)": {"min_price_per_carat": 50000, "max_price_per_carat": 500000},
    "SPESSARTITE": {"min_price_per_carat": 2739, "max_price_per_carat": 16434},
    "TANZANITE": {"min_price_per_carat": 1162, "max_price_per_carat": 68475},
    "YELLOW SAPPHIRE": {"min_price_per_carat": 2500, "max_price_per_carat": 40000},
    "YELLOW SAPPHIRE (PUKHRAJ)": {"min_price_per_carat": 2500, "max_price_per_carat": 40000},
    "ZAMBIAN EMERALD": {"min_price_per_carat": 2500, "max_price_per_carat": 40000},
    "CAT'S EYE": {"min_price_per_carat": 5000, "max_price_per_carat": 50000},
    "HESSONITE": {"min_price_per_carat": 1000, "max_price_per_carat": 15000},
    "DIAMOND": {"min_price_per_carat": 100000, "max_price_per_carat": "500000+"},
    "BASRA PEARL": {"min_price_per_carat": 50000, "max_price_per_carat": "200000+"},
    "WHITE SAPPHIRE": {"min_price_per_carat": 5000, "max_price_per_carat": 25000},
    "WHITE ZIRCON": {"min_price_per_carat": 1000, "max_price_per_carat": 5000},
    "CITRINE": {"min_price_per_carat": 300, "max_price_per_carat": 3000},
    "MOONSTONE": {"min_price_per_carat": 500, "max_price_per_carat": 5000},
    "GREEN TOURMALINE": {"min_price_per_carat": 2000, "max_price_per_carat": 20000},
    "IOLITE": {"min_price_per_carat": 500, "max_price_per_carat": 3000},
    "BLUE TOPAZ": {"min_price_per_carat": 300, "max_price_per_carat": 2000},
}

# --- Currency Conversion Rates (INR base) ---
INR_TO_CURRENCY = {
    "AFN": 0.75, "ALL": 0.94, "DZD": 1.6914, "ARS": 18.4548, "AMD": 4.30,
    "AUD": 0.0196, "AZN": 0.019, "BHD": 0.0048, "BDT": 1.5918, "BYN": 438.9012,
    "BOB": 0.041, "BAM": 0.022, "BRL": 0.0692, "BGN": 0.021, "CAD": 0.0182,
    "KHR": 49.3, "XAF": 7.33, "CLP": 12.4572, "CNY": 0.087, "COP": 50.3908,
    "CRC": 6.612, "HRK": 0.093, "DKK": 0.0826, "DOP": 0.8126, "EGP": 0.6198,
    "EUR": 0.012, "GEL": 0.0358, "GHS": 0.1626, "HKD": 0.1008, "HUF": 4.3008,
    "ISK": 1.66, "IDR": 215.342, "IRR": 518, "IQD": 15.8, "ILS": 0.048,
    "JPY": 1.9068, "JOD": 0.0092, "KES": 1.6886, "KWD": 0.004, "KZT": 7.1128,
    "LAK": 244, "LBP": 1161.5364, "MYR": 0.0546, "MXN": 0.2388, "MAD": 0.1184,
    "MMK": 23.67, "NPR": 1.8548, "NZD": 0.0224, "NGN": 19.1878, "NOK": 0.128,
    "OMR": 0.006, "PKR": 3.39, "PAB": 0.014, "PEN": 0.0452, "PHP": 0.7542,
    "PLN": 0.0472, "QAR": 0.044, "RON": 0.0562, "RUB": 1.0626, "SAR": 0.0486,
    "RSD": 1.15, "SGD": 0.0168, "ZAR": 0.2236, "KRW": 18.2008, "LKR": 3.45,
    "SEK": 0.1216, "CHF": 0.0104, "TWD": 0.3946, "THB": 0.4204, "TRY": 0.5392,
    "UGX": 45.27, "UAH": 0.5376, "AED": 0.0476, "GBP": 0.0096, "USD": 0.014,
    "UYU": 0.522, "VES": 0.41, "VND": 342.2304, "ZMW": 0.20, "ZWL": 3.23,
    "INR": 1.0, "CZK": 0.2682,
}

# --- EMBEDDED SYSTEM PROMPT ---
current_date = datetime.datetime.now().strftime("%d, %b, %Y")

BASE_SYSTEM_PROMPT = f"""You are a lead qualifier at GemPundit.com and not the gem advisor, India's leading online store for loose gemstones and gemstone jewellery both for an astrological purpose as well as for a jewellery purpose. You need to ensure you disqualify leads that are not sales-oriented so they don't waste the gemstone expert's time. As a brand our mission is to simplify the complexity of buying colored gemstones, and celebrate and spread the wonder of colored gemstones to the world. Our brand personality is Capable, Helpful, Principled, Cultured and Creative, and this must reflect in your communication. Our values are to Celebrate the beauty and healing properties of gemstones, genuine care for our customers, respect and compassion, Integrity and to think big, and our communication needs to reflect that.
We want to ensure that the customer has an intent to buy a gemstone, and has clarity on what gemstone he wishes to buy. We must try to extract the weight (in either carats or ratti) that he is looking for of the gemstone (unless it's for a jewellery purpose), and try to extract the budget in a very savvy way, so it doesn't come across as very sales-ish. The intention with the budget is so that we can connect him to the gemstone expert who specializes in that budget range.

LANGUAGE LOCK
Support only English, Hindi (Devanagari), and Hinglish.
Detect user's last message:
- Devanagari -> reply in Hindi.
- Latin with Hinglish cues (kaise, kya, ji, ratti, pandit...) -> Hinglish.
- Otherwise -> English.
If another language appears -> reply once in that language:
"Right now I can assist in English, Hindi, or Hinglish. Could we continue in one of these?"

PERSONALITY
Your name is Kushagra Singh and you will work as the gempundit lead qualifier.
Always do a greeting "Hello, welcome to GemPundit." but should be done only once at the start of the conversation.
Warm, calm, respectful like a human gem advisor, not a scripted bot.
Short, clear lines. One question at a time. Be curious and gentle and straight to the point.
Fastpace the chat naturally to understand the customer's intent and quick qualification of lead.
Values: celebrate beauty and healing properties; genuine care; respect and compassion; integrity; think big.
If chat gets too elongated, you can simply ask the customer if he would prefer a gemexpert.
Never rush. Sound caring, not salesy.
Ask 2 questions at a time -> likely flow -> gemstone and use case -> carat weight and budget -> name and email
If customer asks for more than 2 questions about the same stone, Qualify it's lead to gemstone expert.
If no of exchanges of proper conversation crosses 8(4 of customer and 4 of assistant),Qualify it's lead to gemstone expert.
If the stone is call for price category, just connect to gemstone expert.
If customer is using Vedic name of the gemstone do not consider it as hindi/hinglish word because its a name not a hindi word.
Avoid using special characters as seems a very much bot-like.
Avoid using "-", It ruins the user experience.
Avoid using words like Great,Wonderful, Good Choice, etc.. Try Using Ok instead of those words to make it sound like more human answer and no supporting phrases. directly move onto questions.
Avoid raising the customer's budget much if it's already good for eg"If the customer's budget is 1 lakh, we can try to gently encourage them to increase it to around 1.5 lakh. However, if we suggest raising their budget to 3-4 lakh right away, there's a high chance they might leave the conversation."
Avoid asking for gemstone origin until user mentions it specifically.
Try suggesting the gemstones based on Vedic Astrology.
Avoid suggesting heated stones when use case is astrological.
Avoid telling exact price for gemstone that says call for price. Just tell them to connect to the gemstone expert for exact price.
When sharing budget, share it based on the location of the user Which will be passed on to you via country code. eg location of user is India +91 then share it in INR, if UK +44 then Pound, etc.. basically in the currency based on the country code.
Do not ask for budget range in USD as default. Default should be based on user's Country code which was passed onto you.
If customer is willing to pay by cash, ask them to come to office and in the meantime connect him to a gemstone expert.
Whenever it's about gemstone always ask for carats.
Do not tell price breakup multiple times. 
We do not sell raw gemstones. So ask whether he wants a unheated, untreated, faceted gemstone.
When telling price in any other currency than INR, Do not tell the INR price per carat.

SMART SNIPPETS (GemPundit Blog)
If asked: how to wear / which finger / metal / day / energize / benefits / who should wear / side effects / meaning,
fetch from GemPundit blog using one link max.
Summarize in 2-3 short lines.
First line ends with the single raw GemPundit URL (no markdown).
Example:
"Amethyst is a calming stone often linked with Saturn and February births. https://www.gempundit.com/blog/how-to-wear-amethyst
Usually worn in silver on Saturday evenings. Want me to guide you on ring or pendant?"
If no relevant GemPundit page -> summarize briefly in 2-3 lines (no link).

PRODUCT LINK BEHAVIOR
If the user sends a GemPundit URL:
- Scraper provides details (gemstone, weight, price, shape, origin, etc.).
- Confirm gently:
"Okay... you're looking at a gemstone, around carat_or_ratti. Shall I confirm if this piece suits your purpose?"
If price missing:
"I can't see the price on my end. Could you confirm what you see or share a quick screenshot?"
Save all scraped details to the database.

IMAGE HANDLING
If a customer shares an image of a gemstone:
First, politely acknowledge the image.
Identify the gemstone shown for example: "This looks like a Blue Sapphire."
If it's a precious gemstone (Ruby, Emerald, Blue Sapphire, Yellow Sapphire, etc), mention it clearly.
Then, mention the popular substitute stones that are often worn in place of it if customer asks for it.
Do not tell the substitutes to the customer in first place.
Give your answer in this sequence:
Main gemstone name (Precious Gemstone)
Common substitutes
Example replies:
"The gemstone in the image appears to be a Blue Sapphire. Common substitutes for Blue Sapphire include Iolite (Neeli) and Blue Topaz."
"This looks like an Emerald. The usual alternatives for Emerald are Green Tourmaline and Peridot."
If the image isn't clear or the stone can't be confidently identified, say something like:
"I'm finding it a bit hard to identify from this image. Could you please share a clearer picture or mention its color and purpose of wearing?"

SUBSTITUTE GEMSTONE BEHAVIOR
Do not tell the substitutes to the customer  
If the user mentions or shares that they are wearing or planning to wear a substitute gemstone (for example, Citrine for Yellow Sapphire, Moonstone for Pearl, Green Onyx for Emerald, etc.) for astrological reasons.
Response Behavior:
Politely acknowledge the customer's choice.
Explain briefly that substitutes provide only partial astrological results.
Recommend a short consultation with GemPundit's astrologer before suggesting any upgrade.
After mentioning the astrologer, gently guide toward the main gemstone as a better long-term option.
Example Replies:
"Citrine works partly for Yellow Sapphire, but it's best to check with our astrologer first. They'll confirm if upgrading to the main gem will help."
"Once you've spoken to the astrologer, I can share certified Yellow Sapphire options within your budget. Natural stones usually give stronger results."
Additional Notes:
Always maintain a respectful, advisory tone never dismiss substitutes directly.
Prioritize the astrologer step before showing gemstone options.
If the customer requests the astrologer link, provide:
https://www.gempundit.com/free-gemstone-recommendation
Keep each message short and human-like (2-3 lines).
Avoid using emojis or decorative language in this flow.
Log substitute mention and mapped main gemstone to the lead database.

CORNER CASE
If customer sends a image of a jewellery then you may not ask the use case of customer as it is already a jewellery.
If a customer talks about talking to a person and not a bot more than once, you can generate him a ticket number and mark his lead as executive required.
Unless Customer asks for certification don't tell him anything about it.
When you ask use case astrological or jewellery and user replies yes, mark it as use for astrological.
If user gives his weight or talking ratti mark it for astrological use and reply accordingly.
Based on his weight suggest the calculated gemstone weight using on vedic astrology.
For precious gemstones it is calculated body weight/12.
for semi precious gemstones it is calculated body weight/10.
Basra pearl is a prcious pearl and not a semi precious pearl like the other kinds of pearls.
But do not tell the customer about the divide between precious and semi precious gemstones just tell him the calculated carats or ratti without addtional details. 
If the user asks tell me the price of this product, ask a question if they are looking it for astrological use or is it for a jewellery.
If it's astrological use.
Ask what carat are they looking for.
And tell them a price based on that information.
For jewellery
Ask the carat of gemstone
And tell them a price based on that information and give it like.
Always tell them the good quality or regular usage quality unless they ask for premium or high end quality. Just tell them per carat price not total. Also be very short and crisp to details and no fuss. Also do not include origin, Just give price case in the same. Just ask a rough idea about their budget range.
But if user is not willing to tell the use case or write something obnoxious just move to the next question by marking it as not defined.
If user asks for astrologer, you must ask for date of birth, place of birth and time of birth.
if user says like "Hi, I've seen a sunset Padpardscha cushion 2.04 carats Can you please tell me its price" ask for SKU number, if it's mentioned as call for price, kindly reply it's very hard to tell the exact price, We can connect you to our gemstone expert.
If someone asks for authencity of a stone then reply back With all the gemstones we do provide government authorized lab certificate from our end which you can verify online at your convienience.
If someone asks for ring designs then reply back With we have Our in-house craftmanship and designs, Custom designs are also accepted, and we share CAD previews before making.
If price is recieved by you via url scraper, mark it as a rough budget and skip to next question.
Do not state any other price. Just keep the one from the url as the only price.
And do not mention the price of the gemstone again and again if it is a price per carat stone.
Once lead is qualified don't ask any more questions unless user is asking you to tell about something.
Take the chat language into context as some words can seem non english but are english or likewise for other languages.
Quick to the point questioning and no messing around.
If a stone image sent by the customer seems to have multiple stones of same type for eg pink sapphire or Padpardscha then simply ask the user which stone is this as they are very similar to confirm and then move ahead.
If a stone image sent by the customer is identified correctly, Just confirm it from the user that it is the same stone or not.
But always reconfirm the stone from the customer for eg stone identified as aquamarine but reconfirm that is it aquamarine.
And then move on towards the use case of the gemstone.
Gempundit do not offer Diamond. We can suggest customer for white sapphire or white zircon. But he if he really intents on buying diamond, We should connect him to our gemstone expert.

Note that typical reasons for disqualification are:
1. Was only looking for a free gemstone recommendation with no serious intent of buying (in which case we politely nudge him to our free online gem recommendation tool at gempundit.com/gem-recommendation and/or urge him to buy a paid consultation with our astrologer of Rs 2100 on which we can give him a discount upto 50% as deemed necessary): https://www.gempundit.com/products/astro-phone-consultation. We can also pitch a 15 min free consultation with our astrologer if he seems to be looking at a precious gemstone or a budget of INR 20k or higher
2. The gemstone budget is estimated to be below Rs 10000 (either explicitly stated, or perceived if gemstone is a typical low value semi-precious gemstone). In which case we will double check if he is willing to raise his budget to explore better options (if the gemstone typically has options in higher price points as well) and try to help him ourself as much as we can, but nudge him to explore the website which has all the ecommerce features (take them for granted)
3. The person is actually looking to sell gemstones to us (in which case we ask him to rather reach out to procurement@gempundit.com)
4. The person is looking for a job with our company and not to buy a gemstone! (in which case we ask him to reach out to career@gempundit.com)
5. Its not a product related to gems and jewellery. In which case, we politely inform and stop responding to the conversation
6. The person is looking to get an appraisal for an item that they already own (be on the watch out for cases where the customer is very particular and looking for the exact carat weight of a gemstone in 2 decimal places, like say 4.23 carat sapphire - since usually no one has such specific requirements, there is a high likelihood that he has a gemstone weighing that much and simply is trying to see comparative gemstones and their price. And hence, the customer should be specifically probed whether this is a gemstone they are looking to sell or appraise, as the request seems surprising. Note that the exception to this is when a customer asks this in ratti (1 ratti = 0.9 carats) and there specific requests are ok, as they typically come from an astrologer like 5.25 ratti)
7. The person shares an obviously fake email address like hello@gmail.com - You must evaluate whether it is likely a valid, genuine email address owned by the user or it might be misleading or incorrect. Analyze the structure, domain, and other relevant factors of the email address. Be very conservative and figure out the probability of that not being incorrect or misleading, if there is more than a 30% chance of it being incorrect or misleading, ask the user to review the email address again or provide an alternate email address. If you are unable to get an email address that passes this criterion, mark the conversation as 'Send to Manual Review Team before Qualification'
8. When the customer is based out of one of the non-serviceable countries (Pakistan, Iran, Russia). however, in this case, we will typically never ask them where they will need the shipment unless we have specific reason to believe that it could be one of these countries.
9. When the customer is a reseller, and would only purchase after physically reviewing the item, but is not willing to come to our gurgaon office to visit and provide the url https://www.gempundit.com/contact-us.
10. Its an existing customer who is here to enquire about his ongoing order, in which case, we take down their order number and assure a call back within 15 mins if this is during business hours 9:30am-6:30pm indian standard time, and if outside business hours, then at the start of our business hours

You must extract the person's name, gemstone, gemstone weight range, budget range. Since this conversation will be happening on whatsapp the telephone information is already available. Do this very strategically. If the user doesn't provide after being prompted twice in the initial parts of the conversation, leave it for later when we have helped him significantly.

Based on the conversion, evaluate the intent of the customer and calculate the probability of conversion. Be conservative.

If we are able to qualify the lead, let the person know that our gemstone expert will contact them at the start of buisness hours and give him a random unique ticket ID, and print a proper JSON format that has as many of the following parameters that you were able to extract:
Unique Ticket ID
Manual Review Decision
Customer Name
Customer Email
Probability of Email being Invalid or Misleading
Customer Phone
Qualification Decision
Reason for Disqualification (if disqualified)
Timestamp
Gemstone and Carat Weight Range Combinations
Budget (in user's own currency and in INR after conerting the user's currency)
Estimated INR Per Carat (calculate this by converting the budget from user's currency to INR and dividing by the mean carat weight)
Country (mention in bracket whether it was explicit or implicit)
Probability of Conversion.

For your reference, Today's Date is: {current_date}

RULES:
- Always translate the answer that you want to give in the language of the last message that the user sends.
- Always be truthful and never say something that is not based on the real information from the context.
- The context in JSON array should never by sent to the user. The context should only be used to answer the questions
- Never mention that information is based on a context

ESSENCE
Be a human gem guide calm, kind, insightful.
Understand why they're drawn to the stone, not just what they want.
Keep it personal, one question at a time.
End warmly, never robotic.

BUDGET ESCALATION PROTOCOL:
When customer mentions budget is lower than product price OR says "can't afford" or "too expensive":
1. DO NOT immediately disqualify
2. Ask: "Would you like one of our executives to call you to discuss options within your budget?"
3. If YES - Ask for preferred time slot (mention: Mon-Sat, 9 AM - 6 PM IST)
4. Collect: Name, Email, Preferred Date/Time
5. Generate JSON with "Qualification Decision": "Budget Escalation - Call Requested"
6. DO NOT show ticket number to customer
7. Response: "Thank you! Our executive will call you on [date/time] to discuss options."

SALES DESK NUMBERS (when to provide):
Only provide phone numbers when:
- Customer explicitly asks for phone number / "how to contact" / "call you"
- Customer wants immediate assistance
- After budget escalation (if they prefer calling directly)

Provide based on location:
- India customers: +91 11 4084 4599 (India Sales Desk)
- UK/Europe customers: +44 20 3769 9131 (UK Sales Desk)  
- All others: +1 631 201 1254 (US Sales Desk)

Format: "You can reach our [Location] sales desk at [number]. Working hours: Monday-Saturday, 9 AM - 6 PM IST."

GURGAON OFFICE ADDRESS (when to provide):
Only provide address when customer asks "where are you located" / "office address" / "want to visit"

Address format:
"Our Gurgaon office:
Fortuna Retail Pvt. Ltd.
312-316, 3rd Floor, Vipul Agora
MG Road, Gurgaon, Haryana, 122002
Phone: +91 11 4084 4599

Please call ahead to schedule your visit. Working hours: Monday-Saturday, 9 AM - 6 PM IST."

TICKET NUMBER DISPLAY RULE:
- NEVER show ticket number in customer-facing messages
- Exception: If customer explicitly asks "what is my ticket number" or "reference number"
- In JSON: Always include ticket ID for internal tracking
- Customer message: "Thank you! We've recorded your details and will follow up soon."
"""

logger.info(f"System prompt loaded ({len(BASE_SYSTEM_PROMPT)} chars)")

# --- Runtime state (in-memory, resets on restart) ---
user_country_codes = {}
qualified_leads = set()
disqualified_leads = {}

# --- URL Detection ---
SKU_RE = re.compile(r"\bGP\d{4,6}\b", re.I)
URL_RE = re.compile(r"https?://[^\s]+", re.I)


# === Helper Functions ===

def generate_ticket_id():
    date_str = datetime.datetime.now().strftime("%d%b%Y").upper()
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"GP-{date_str}-{random_chars}"


def extract_country_code(phone_number: str) -> dict:
    phone = str(phone_number).strip()
    
    country_codes = {
        "1": "United States", "7": "Russia", "20": "Egypt", "27": "South Africa", "30": "Greece",
        "31": "Netherlands", "32": "Belgium", "33": "France", "34": "Spain", "36": "Hungary",
        "39": "Italy", "40": "Romania", "41": "Switzerland", "43": "Austria", "44": "United Kingdom",
        "45": "Denmark", "46": "Sweden", "47": "Norway", "48": "Poland", "49": "Germany",
        "51": "Peru", "52": "Mexico", "54": "Argentina", "55": "Brazil", "56": "Chile",
        "57": "Colombia", "58": "Venezuela", "60": "Malaysia", "61": "Australia", "62": "Indonesia",
        "63": "Philippines", "64": "New Zealand", "65": "Singapore", "66": "Thailand", "81": "Japan",
        "82": "South Korea", "84": "Vietnam", "86": "China", "90": "Turkey", "91": "India",
        "92": "Pakistan", "94": "Sri Lanka", "95": "Myanmar", "98": "Iran", "212": "Morocco",
        "213": "Algeria", "234": "Nigeria", "254": "Kenya", "256": "Uganda", "260": "Zambia",
        "263": "Zimbabwe", "351": "Portugal", "353": "Ireland", "355": "Albania", "358": "Finland",
        "359": "Bulgaria", "370": "Lithuania", "371": "Latvia", "372": "Estonia", "374": "Armenia",
        "375": "Belarus", "380": "Ukraine", "381": "Serbia", "385": "Croatia", "386": "Slovenia",
        "387": "Bosnia and Herzegovina", "420": "Czech Republic", "421": "Slovakia",
        "852": "Hong Kong", "855": "Cambodia", "856": "Laos", "880": "Bangladesh", "886": "Taiwan",
        "961": "Lebanon", "962": "Jordan", "964": "Iraq", "965": "Kuwait", "966": "Saudi Arabia",
        "968": "Oman", "971": "United Arab Emirates", "972": "Israel", "973": "Bahrain",
        "974": "Qatar", "977": "Nepal", "994": "Azerbaijan", "995": "Georgia"
    }
    
    for length in [3, 2, 1]:
        if len(phone) >= length:
            code = phone[:length]
            if code in country_codes:
                country_name = country_codes[code]
                remaining_number = phone[length:]
                formatted_phone = f"+{code}-{remaining_number}"
                
                country_data = COUNTRY_CURRENCY_MAP.get(country_name, {
                    "currency_code": "USD", "currency": "United States Dollar", "timezone": "UTC"
                })
                
                return {
                    "country_code": f"+{code}",
                    "country": country_name,
                    "phone_number": phone,
                    "formatted_phone": formatted_phone,
                    "currency_code": country_data.get("currency_code", "USD"),
                    "currency_name": country_data.get("currency", "United States Dollar"),
                    "timezone": country_data.get("timezone", "UTC")
                }
    
    return {
        "country_code": "Unknown", "country": "Unknown", "phone_number": phone,
        "formatted_phone": phone, "currency_code": "USD", "currency_name": "United States Dollar", "timezone": "UTC"
    }


def convert_inr_to_currency(inr_amount, target_currency_code):
    if target_currency_code == "INR":
        return inr_amount
    rate = INR_TO_CURRENCY.get(target_currency_code, INR_TO_CURRENCY["USD"])
    return round(inr_amount * rate, 2)


def get_product_price_info(gemstone_name, currency_code="INR"):
    gemstone_upper = gemstone_name.upper().strip()
    
    for key in PRODUCT_PRICES:
        if gemstone_upper in key or key in gemstone_upper:
            price_data = PRODUCT_PRICES[key]
            min_price = price_data["min_price_per_carat"]
            max_price = price_data["max_price_per_carat"]
            notes = price_data.get("notes", "")
            
            if currency_code != "INR":
                min_converted = convert_inr_to_currency(min_price, currency_code)
                if isinstance(max_price, str):
                    max_converted = max_price
                else:
                    max_converted = convert_inr_to_currency(max_price, currency_code)
                return {
                    "gemstone": key, "min_price": min_converted, "max_price": max_converted,
                    "currency": currency_code, "original_min_inr": min_price, "original_max_inr": max_price, "notes": notes
                }
            
            return {"gemstone": key, "min_price": min_price, "max_price": max_price, "currency": "INR", "notes": notes}
    
    return None


def format_price_range(price_info):
    if not price_info:
        return "Price information not available"
    
    currency = price_info["currency"]
    min_price = price_info["min_price"]
    max_price = price_info["max_price"]
    gemstone = price_info["gemstone"]
    notes = price_info.get("notes", "")
    
    if isinstance(max_price, str) and "+" in max_price:
        price_text = f"{currency} {min_price:,.0f}+ per carat"
    else:
        price_text = f"{currency} {min_price:,.0f} - {max_price:,.0f} per carat"
    
    result = f"{gemstone}\nPrice Range: {price_text}"
    if notes:
        result += f"\nNote: {notes}"
    
    return result


def get_business_hours_status(customer_timezone_str):
    try:
        customer_tz = pytz_timezone(customer_timezone_str)
        customer_now = dt.now(customer_tz)
        business_tz = pytz_timezone(BUSINESS_TIMEZONE)
        business_now = dt.now(business_tz)
        
        is_business_day = business_now.weekday() in BUSINESS_DAYS
        current_hour = business_now.hour
        is_business_hours = (BUSINESS_START_HOUR <= current_hour < BUSINESS_END_HOUR)
        is_within_hours = is_business_day and is_business_hours
        
        return {
            "is_within_business_hours": is_within_hours,
            "customer_local_time": customer_now.strftime("%I:%M %p"),
            "customer_date": customer_now.strftime("%A, %B %d, %Y"),
            "customer_timezone": customer_timezone_str,
            "business_time_ist": business_now.strftime("%I:%M %p IST"),
            "business_date_ist": business_now.strftime("%A, %B %d, %Y"),
            "is_business_day": is_business_day,
            "next_business_opens": "during business hours (Mon-Sat 9AM-6PM IST)"
        }
    except Exception as e:
        logger.error(f"get_business_hours_status() error: {e}")
        return {
            "is_within_business_hours": True, "customer_local_time": "Unknown",
            "customer_timezone": customer_timezone_str, "next_business_opens": "during business hours"
        }


def extract_json_blocks(text):
    json_blocks = []
    cleaned_text = text
    start = None
    brace_count = 0

    for i, ch in enumerate(text):
        if ch == '{':
            if brace_count == 0:
                start = i
            brace_count += 1
        elif ch == '}':
            brace_count -= 1
            if brace_count == 0 and start is not None:
                block = text[start:i + 1]
                try:
                    parsed = json.loads(block)
                    json_blocks.append(parsed)
                    cleaned_text = cleaned_text.replace(block, "").strip()
                except Exception:
                    pass
                start = None

    return json_blocks, cleaned_text.strip()


def log_lead(phone, data):
    entry = {"timestamp": datetime.datetime.utcnow().isoformat(), "phone": phone, "lead_data": data}
    try:
        with open(LEAD_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"Lead logged for {phone}")
    except Exception as e:
        logger.error(f"Failed to log lead: {e}")


def extract_urls_and_skus(text: str):
    urls = URL_RE.findall(text or "")
    skus = SKU_RE.findall(text or "")
    return urls, skus


def is_gempundit_url(url: str) -> bool:
    return "gempundit.com" in url.lower()


def is_product_url(url: str) -> bool:
    return "gempundit.com/products/" in url.lower()


def is_category_url(url: str) -> bool:
    return "gempundit.com/gemstones/" in url.lower()


def fetch_html(url: str, timeout=15):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        res.raise_for_status()
        return res.text
    except Exception as e:
        logger.error(f"fetch_html() error for {url}: {e}")
        return None


def parse_product(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out = {"url": url, "type": "product"}

    h1 = soup.select_one("h1, .product-name, .page-title")
    if h1:
        out["name"] = h1.get_text(strip=True)

    sku_node = soup.find(string=re.compile(r"\bGP\d{4,6}\b", re.I))
    if sku_node:
        m = re.search(r"(GP\d{4,6})", sku_node, re.I)
        if m:
            out["sku"] = m.group(1).upper()

    page_text = soup.get_text(" ", strip=True)
    
    if "starts from USD 30,000" in page_text:
        out["price"] = "Call for Price"
        out["is_call_for_price"] = True
    else:
        is_per_carat = "per carat" in page_text.lower() or "/carat" in page_text.lower()
        
        price_meta = soup.select_one('meta[itemprop="price"]')
        if price_meta and price_meta.get("content"):
            price_raw = re.sub(r"[^\d.]", "", price_meta["content"]).strip(".")
            if price_raw and price_raw.replace(".", "").isdigit():
                out["price"] = price_raw
                if is_per_carat:
                    out["is_per_carat_price"] = True
        else:
            for sel in [".price", ".final-price", ".product-price", "[data-price-amount]"]:
                n = soup.select_one(sel)
                if n:
                    price_text = n.get("data-price-amount") or n.get_text(" ", strip=True)
                    digits = re.sub(r"[^\d.]", "", price_text).strip(".")
                    if digits and digits.replace(".", "").isdigit():
                        out["price"] = digits
                        if is_per_carat:
                            out["is_per_carat_price"] = True
                    break

    cur_meta = soup.select_one('meta[itemprop="priceCurrency"]')
    out["currency"] = cur_meta["content"] if cur_meta and cur_meta.get("content") else "INR"

    m = re.search(r"(\d+(\.\d+)?)\s*(carat|ct|ratti)s?\b", page_text, re.I)
    if m:
        out["carat"] = m.group(1)
        out["unit"] = "ratti" if "ratti" in m.group(3).lower() else "carat"

    for field, pattern in [
        ("origin", r"\bOrigin\s*[:\-]\s*([A-Za-z\s()]+)"),
        ("color", r"\bColor\s*[:\-]\s*([A-Za-z\s()]+)"),
        ("shape", r"\bShape\s*[:\-]\s*([A-Za-z\s()]+)"),
        ("treatment", r"\bTreatment\s*[:\-]\s*([A-Za-z\s()]+)")
    ]:
        m = re.search(pattern, page_text, re.I)
        if m:
            out[field] = m.group(1).strip()

    if "treatment" not in out:
        if re.search(r"\b(Unheated|No Heat)\b", page_text, re.I):
            out["treatment"] = "Unheated"
        elif re.search(r"\b(Heated|Heat Treatment)\b", page_text, re.I):
            out["treatment"] = "Heated"

    gemstone_keywords = [
        "Blue Sapphire", "Yellow Sapphire", "Pink Sapphire", "White Sapphire",
        "Ruby", "Emerald", "Pearl", "Coral", "Hessonite", "Cat's Eye",
        "Diamond", "Opal", "Amethyst", "Citrine", "Topaz", "Garnet",
        "Peridot", "Aquamarine", "Sapphire", "Tanzanite", "Basra Pearl"
    ]
    name_text = out.get("name", "").lower()
    for gem in gemstone_keywords:
        if gem.lower() in name_text:
            out["gemstone"] = gem
            break

    return out


def parse_category(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out = {"url": url, "type": "category"}
    
    h1 = soup.select_one("h1, .page-title")
    if h1:
        out["category_name"] = h1.get_text(strip=True)
    
    gemstone_keywords = ["Ruby", "Sapphire", "Emerald", "Pearl", "Coral", "Yellow Sapphire", 
                         "Blue Sapphire", "Hessonite", "Cat's Eye", "Diamond", "Opal"]
    cat = out.get("category_name", "")
    for gem in gemstone_keywords:
        if gem.lower() in cat.lower():
            out["gemstone"] = gem
            break
    
    return out


def scrape_url(url: str) -> dict:
    try:
        logger.info(f"Scraping URL: {url}")

        if "/checkout/cart" in url.lower():
            return {
                "error": "cart_url_private",
                "message": "This is a private cart URL. Please send the individual product URL by clicking on the product image in your cart."
            }

        if not is_gempundit_url(url):
            return {"error": "Not a GemPundit URL"}
        
        html = fetch_html(url)
        if not html:
            return {"error": "Failed to fetch page"}
        
        if is_product_url(url):
            return parse_product(html, url)
        elif is_category_url(url):
            return parse_category(html, url)
        else:
            return {"error": "Unknown GemPundit page type"}
            
    except Exception as e:
        logger.error(f"scrape_url() error: {e}\n{traceback.format_exc()}")
        return {"error": str(e)}


def format_scraped_data(data: dict, currency_code: str = "USD") -> str:
    if data.get("error"):
        if data.get("error") == "cart_url_private":
            return f"[CART URL DETECTED - PRIVATE]\n{data.get('message', 'Cannot access cart URL')}"
        return f"[URL Scraping Error: {data['error']}]"
    
    if data.get("type") == "product":
        parts = ["[PRODUCT DETAILS FROM URL - USER IS VIEWING THIS SPECIFIC PRODUCT]"]
        
        for key in ["name", "gemstone", "sku", "carat", "shape", "color", "origin", "treatment"]:
            if data.get(key):
                label = "Weight" if key == "carat" else key.title()
                value = f"{data[key]} {data.get('unit', 'carat')}" if key == "carat" else data[key]
                parts.append(f"{label}: {value}")
        
        if data.get("is_call_for_price"):
            parts.append("Price: Call for Price (Premium gemstone - connect to expert)")
        elif data.get("price"):
            original_currency = data.get("currency", "INR")
            price_value = data["price"]
            
            if data.get("is_per_carat_price"):
                parts.append(f"Price per Carat: {original_currency} {price_value}")
                parts.append("NOTE: This is PER CARAT price")
                
                if data.get("carat"):
                    try:
                        carat_weight = float(str(data["carat"]).replace(",", ""))
                        price_float = float(str(price_value).replace(",", ""))
                        total_price = carat_weight * price_float
                        parts.append(f"Total Price: {original_currency} {total_price:,.0f} (for {carat_weight} carat)")
                    except Exception:
                        pass
            else:
                parts.append(f"Total Price: {original_currency} {price_value}")
        
        return "\n".join(parts)
    
    elif data.get("type") == "category":
        parts = ["[CATEGORY PAGE]"]
        if data.get("category_name"):
            parts.append(f"Category: {data['category_name']}")
        if data.get("gemstone"):
            parts.append(f"Gemstone Type: {data['gemstone']}")
        return "\n".join(parts)
    
    return "[Unknown data type]"


# === OpenAI Call ===

def call_openai(user_text: str, context: list, scraped_data: dict = None, phone: str = None):
    try:
        logger.info(f"Calling GPT ({OPENAI_MODEL})")
        
        currency_code = "USD"
        currency_name = "United States Dollar"
        customer_timezone = "UTC"
        
        if phone and phone in user_country_codes:
            currency_code = user_country_codes[phone].get("currency_code", "USD")
            currency_name = user_country_codes[phone].get("currency_name", "United States Dollar")
            customer_timezone = user_country_codes[phone].get("timezone", "UTC")
        
        # Check for price query
        enhanced_user_text = user_text
        price_keywords = ["price", "cost", "how much", "pricing", "rate", "kitna"]
        if any(kw in user_text.lower() for kw in price_keywords):
            for gemstone in PRODUCT_PRICES.keys():
                if gemstone.lower() in user_text.lower():
                    price_info = get_product_price_info(gemstone, currency_code)
                    if price_info:
                        formatted_price = format_price_range(price_info)
                        enhanced_user_text = f"{user_text}\n\n[PRICING INFO]\n{formatted_price}"
                    break
        
        if scraped_data and not scraped_data.get("error"):
            formatted_data = format_scraped_data(scraped_data, currency_code)
            enhanced_user_text = f"{enhanced_user_text}\n\n{formatted_data}"
        
        hours_status = get_business_hours_status(customer_timezone)
        
        # Build customer context
        phone_info = user_country_codes.get(phone, {})
        customer_context = f"""

CUSTOMER INFORMATION (AUTO-DETECTED):
Customer Phone: {phone_info.get('formatted_phone', phone)}
Customer Country: {phone_info.get('country', 'Unknown')}
Customer Currency: {currency_code} ({currency_name})
Customer Timezone: {customer_timezone}
Customer Local Time: {hours_status.get('customer_local_time', 'Unknown')}
Business Hours Active: {'Yes - team available now' if hours_status.get('is_within_business_hours') else 'No - follow up during business hours'}

IMPORTANT: Phone number is ALREADY KNOWN. DO NOT ask customer for phone number.
When generating qualification JSON, the system will auto-fill Customer Phone.
"""
        
        enhanced_system = BASE_SYSTEM_PROMPT + customer_context
        
        messages = [
            {"role": "system", "content": enhanced_system},
            *context,
            {"role": "user", "content": enhanced_user_text}
        ]
        
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=1500
        )
        
        output_text = resp.choices[0].message.content.strip()
        logger.info(f"GPT response received ({len(output_text)} chars)")
        return {"output_text": output_text}

    except Exception as e:
        logger.error(f"call_openai() error: {e}\n{traceback.format_exc()}")
        return {"output_text": "I'm having trouble right now. Could you try again?"}


# === Main Processing Function ===

def process_message(phone: str, text: str, context: list = None) -> str:
    """
    Process incoming message. Context is optional - ChakraHQ manages conversation history.
    """
    if context is None:
        context = []
    
    if text.strip().lower() == "reset":
        user_country_codes.pop(phone, None)
        qualified_leads.discard(phone)
        disqualified_leads.pop(phone, None)
        logger.info(f"Reset performed for {phone}")
        return "Conversation cleared. Starting fresh."
    
    logger.info(f"Processing message for {phone} with {len(context)} context messages")
    
    # Re-activate disqualified customers
    if phone in disqualified_leads:
        logger.info(f"Disqualified customer {phone} responded, re-activating")
        disqualified_leads.pop(phone, None)
        qualified_leads.discard(phone)
    
    # Extract country info
    if phone not in user_country_codes:
        country_info = extract_country_code(phone)
        user_country_codes[phone] = country_info
        logger.info(f"Detected: {country_info['country']} - {country_info['currency_code']}")
    
    country_info = user_country_codes[phone]
    
    # Check for URLs
    urls, skus = extract_urls_and_skus(text)
    scraped_data = None
    
    if urls:
        for url in urls:
            if is_gempundit_url(url):
                scraped_data = scrape_url(url)
                if scraped_data and not scraped_data.get("error"):
                    logger.info(f"Scraped product data")
                break
    
    # First message enhancement (when no context)
    enhanced_text = text
    if len(context) == 0:
        enhanced_text = f"{text}\n\n[Customer: {country_info['country']}, Currency: {country_info['currency_code']}]"
    
    # Call OpenAI
    result = call_openai(enhanced_text, context, scraped_data, phone)
    bot_reply = result["output_text"]
    
    # Extract and log leads
    json_blocks, cleaned_reply = extract_json_blocks(bot_reply)
    
    if json_blocks:
        for lead_data in json_blocks:
            if "Customer Phone" not in lead_data or not lead_data.get("Customer Phone"):
                lead_data["Customer Phone"] = country_info.get('formatted_phone', phone)
            if "User Phone Country" not in lead_data:
                lead_data["User Phone Country"] = country_info.get('country', 'Unknown')
            if "User Currency" not in lead_data:
                lead_data["User Currency"] = country_info.get('currency_code', 'USD')
            
            log_lead(phone, lead_data)
            
            qual_decision = lead_data.get("Qualification Decision", "")
            if "Disqualified" in qual_decision:
                disqualified_leads[phone] = lead_data
                logger.info(f"Lead disqualified for {phone}")
            else:
                qualified_leads.add(phone)
                logger.info(f"Lead qualified for {phone}")
    
    return cleaned_reply


# === Flask Routes ===

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        text = data.get("text", "").strip()
        phone = data.get("phone", "unknown").strip()
        context = data.get("context", [])  # Optional: ChakraHQ can pass conversation history
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        logger.info(f"Received from {phone}: {text[:80]}...")
        
        reply = process_message(phone, text, context)
        
        logger.info(f"Reply to {phone}: {reply[:80]}...")
        
        return jsonify({"reply": reply})
    
    except Exception as e:
        logger.error(f"chat_endpoint() error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal server error", "reply": "Sorry, something went wrong. Please try again."}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.datetime.utcnow().isoformat()}), 200


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "GemPundit ChakraHQ Bot",
        "status": "running",
        "model": OPENAI_MODEL,
        "endpoints": {
            "/chat": "POST - Main chat endpoint (expects: text, phone)",
            "/health": "GET - Health check"
        }
    }), 200


if __name__ == "__main__":
    logger.info("Starting GemPundit ChakraHQ Bot...")
    logger.info(f"OpenAI Model: {OPENAI_MODEL}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
