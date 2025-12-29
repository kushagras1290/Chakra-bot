import os
import json
import time
import threading
import uuid
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
from pytz import time
import threadingzone as pytz_timezone, utc
from datetime import datetime as dt

# === Setup ===
load_dotenv()
app = Flask(__name__)

# --- Config ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PORT = int(os.getenv("PORT", 3099))

# --- Business Hours Configuration (IST) ---
BUSINESS_TIMEZONE = "Asia/Kolkata"  # IST
BUSINESS_START_HOUR = 9  # 9 AM IST
BUSINESS_END_HOUR = 18   # 6 PM IST
BUSINESS_DAYS = [0, 1, 2, 3, 4, 5]  # Monday to Friday (0=Monday, 6=Sunday)

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

# --- Country & Currency Data with Timezones ---
COUNTRY_CURRENCY_MAP = {
    "Afghanistan": {"calling_code": "+93", "currency_code": "AFN", "currency": "Afghan Afghani", "timezone": "Asia/Kabul"},
    "Albania": {"calling_code": "+355", "currency_code": "ALL", "currency": "Albanian Lek", "timezone": "Europe/Tirane"},
    "Algeria": {"calling_code": "+213", "currency_code": "DZD", "currency": "Algerian Dinar", "timezone": "Africa/Algiers"},
    "Argentina": {"calling_code": "+54", "currency_code": "ARS", "currency": "Argentine Peso", "timezone": "America/Argentina/Buenos_Aires"},
    "Armenia": {"calling_code": "+374", "currency_code": "AMD", "currency": "Armenian Dram", "timezone": "Asia/Yerevan"},
    "Australia": {"calling_code": "+61", "currency_code": "AUD", "currency": "Australian Dollar", "timezone": "Australia/Sydney"},
    "Austria": {"calling_code": "+43", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Vienna"},
    "Azerbaijan": {"calling_code": "+994", "currency_code": "AZN", "currency": "Azerbaijani Manat", "timezone": "Asia/Baku"},
    "Bahrain": {"calling_code": "+973", "currency_code": "BHD", "currency": "Bahraini Dinar", "timezone": "Asia/Bahrain"},
    "Bangladesh": {"calling_code": "+880", "currency_code": "BDT", "currency": "Bangladeshi Taka", "timezone": "Asia/Dhaka"},
    "Belarus": {"calling_code": "+375", "currency_code": "BYN", "currency": "Belarusian Ruble", "timezone": "Europe/Minsk"},
    "Belgium": {"calling_code": "+32", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Brussels"},
    "Bolivia": {"calling_code": "+591", "currency_code": "BOB", "currency": "Bolivian Boliviano", "timezone": "America/La_Paz"},
    "Bosnia and Herzegovina": {"calling_code": "+387", "currency_code": "BAM", "currency": "Convertible Mark", "timezone": "Europe/Sarajevo"},
    "Brazil": {"calling_code": "+55", "currency_code": "BRL", "currency": "Brazilian Real", "timezone": "America/Sao_Paulo"},
    "Bulgaria": {"calling_code": "+359", "currency_code": "BGN", "currency": "Bulgarian Lev", "timezone": "Europe/Sofia"},
    "Cambodia": {"calling_code": "+855", "currency_code": "KHR", "currency": "Cambodian Riel", "timezone": "Asia/Phnom_Penh"},
    "Cameroon": {"calling_code": "+237", "currency_code": "XAF", "currency": "Central African CFA Franc", "timezone": "Africa/Douala"},
    "Canada": {"calling_code": "+1", "currency_code": "CAD", "currency": "Canadian Dollar", "timezone": "America/Toronto"},
    "Chile": {"calling_code": "+56", "currency_code": "CLP", "currency": "Chilean Peso", "timezone": "America/Santiago"},
    "China": {"calling_code": "+86", "currency_code": "CNY", "currency": "Chinese Yuan", "timezone": "Asia/Shanghai"},
    "Colombia": {"calling_code": "+57", "currency_code": "COP", "currency": "Colombian Peso", "timezone": "America/Bogota"},
    "Costa Rica": {"calling_code": "+506", "currency_code": "CRC", "currency": "Costa Rican Colón", "timezone": "America/Costa_Rica"},
    "Croatia": {"calling_code": "+385", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Zagreb"},
    "Cyprus": {"calling_code": "+357", "currency_code": "EUR", "currency": "Euro", "timezone": "Asia/Nicosia"},
    "Czech Republic": {"calling_code": "+420", "currency_code": "CZK", "currency": "Czech Koruna", "timezone": "Europe/Prague"},
    "Denmark": {"calling_code": "+45", "currency_code": "DKK", "currency": "Danish Krone", "timezone": "Europe/Copenhagen"},
    "Dominican Republic": {"calling_code": "+1-809", "currency_code": "DOP", "currency": "Dominican Peso", "timezone": "America/Santo_Domingo"},
    "Ecuador": {"calling_code": "+593", "currency_code": "USD", "currency": "United States Dollar", "timezone": "America/Guayaquil"},
    "Egypt": {"calling_code": "+20", "currency_code": "EGP", "currency": "Egyptian Pound", "timezone": "Africa/Cairo"},
    "El Salvador": {"calling_code": "+503", "currency_code": "USD", "currency": "United States Dollar", "timezone": "America/El_Salvador"},
    "Estonia": {"calling_code": "+372", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Tallinn"},
    "Finland": {"calling_code": "+358", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Helsinki"},
    "France": {"calling_code": "+33", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Paris"},
    "Georgia": {"calling_code": "+995", "currency_code": "GEL", "currency": "Georgian Lari", "timezone": "Asia/Tbilisi"},
    "Germany": {"calling_code": "+49", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Berlin"},
    "Ghana": {"calling_code": "+233", "currency_code": "GHS", "currency": "Ghanaian Cedi", "timezone": "Africa/Accra"},
    "Greece": {"calling_code": "+30", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Athens"},
    "Hong Kong": {"calling_code": "+852", "currency_code": "HKD", "currency": "Hong Kong Dollar", "timezone": "Asia/Hong_Kong"},
    "Hungary": {"calling_code": "+36", "currency_code": "HUF", "currency": "Hungarian Forint", "timezone": "Europe/Budapest"},
    "Iceland": {"calling_code": "+354", "currency_code": "ISK", "currency": "Icelandic Króna", "timezone": "Atlantic/Reykjavik"},
    "India": {"calling_code": "+91", "currency_code": "INR", "currency": "Indian Rupee", "timezone": "Asia/Kolkata"},
    "Indonesia": {"calling_code": "+62", "currency_code": "IDR", "currency": "Indonesian Rupiah", "timezone": "Asia/Jakarta"},
    "Iran": {"calling_code": "+98", "currency_code": "IRR", "currency": "Iranian Rial", "timezone": "Asia/Tehran"},
    "Iraq": {"calling_code": "+964", "currency_code": "IQD", "currency": "Iraqi Dinar", "timezone": "Asia/Baghdad"},
    "Ireland": {"calling_code": "+353", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Dublin"},
    "Israel": {"calling_code": "+972", "currency_code": "ILS", "currency": "Israeli New Shekel", "timezone": "Asia/Jerusalem"},
    "Italy": {"calling_code": "+39", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Rome"},
    "Japan": {"calling_code": "+81", "currency_code": "JPY", "currency": "Japanese Yen", "timezone": "Asia/Tokyo"},
    "Jordan": {"calling_code": "+962", "currency_code": "JOD", "currency": "Jordanian Dinar", "timezone": "Asia/Amman"},
    "Kenya": {"calling_code": "+254", "currency_code": "KES", "currency": "Kenyan Shilling", "timezone": "Africa/Nairobi"},
    "Kuwait": {"calling_code": "+965", "currency_code": "KWD", "currency": "Kuwaiti Dinar", "timezone": "Asia/Kuwait"},
    "Laos": {"calling_code": "+856", "currency_code": "LAK", "currency": "Lao Kip", "timezone": "Asia/Vientiane"},
    "Latvia": {"calling_code": "+371", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Riga"},
    "Lebanon": {"calling_code": "+961", "currency_code": "LBP", "currency": "Lebanese Pound", "timezone": "Asia/Beirut"},
    "Lithuania": {"calling_code": "+370", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Vilnius"},
    "Luxembourg": {"calling_code": "+352", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Luxembourg"},
    "Malaysia": {"calling_code": "+60", "currency_code": "MYR", "currency": "Malaysian Ringgit", "timezone": "Asia/Kuala_Lumpur"},
    "Mexico": {"calling_code": "+52", "currency_code": "MXN", "currency": "Mexican Peso", "timezone": "America/Mexico_City"},
    "Morocco": {"calling_code": "+212", "currency_code": "MAD", "currency": "Moroccan Dirham", "timezone": "Africa/Casablanca"},
    "Myanmar": {"calling_code": "+95", "currency_code": "MMK", "currency": "Myanmar Kyat", "timezone": "Asia/Yangon"},
    "Nepal": {"calling_code": "+977", "currency_code": "NPR", "currency": "Nepalese Rupee", "timezone": "Asia/Kathmandu"},
    "Netherlands": {"calling_code": "+31", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Amsterdam"},
    "New Zealand": {"calling_code": "+64", "currency_code": "NZD", "currency": "New Zealand Dollar", "timezone": "Pacific/Auckland"},
    "Nigeria": {"calling_code": "+234", "currency_code": "NGN", "currency": "Nigerian Naira", "timezone": "Africa/Lagos"},
    "Norway": {"calling_code": "+47", "currency_code": "NOK", "currency": "Norwegian Krone", "timezone": "Europe/Oslo"},
    "Oman": {"calling_code": "+968", "currency_code": "OMR", "currency": "Omani Rial", "timezone": "Asia/Muscat"},
    "Pakistan": {"calling_code": "+92", "currency_code": "PKR", "currency": "Pakistani Rupee", "timezone": "Asia/Karachi"},
    "Panama": {"calling_code": "+507", "currency_code": "PAB", "currency": "Panamanian Balboa", "timezone": "America/Panama"},
    "Peru": {"calling_code": "+51", "currency_code": "PEN", "currency": "Peruvian Sol", "timezone": "America/Lima"},
    "Philippines": {"calling_code": "+63", "currency_code": "PHP", "currency": "Philippine Peso", "timezone": "Asia/Manila"},
    "Poland": {"calling_code": "+48", "currency_code": "PLN", "currency": "Polish Złoty", "timezone": "Europe/Warsaw"},
    "Portugal": {"calling_code": "+351", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Lisbon"},
    "Qatar": {"calling_code": "+974", "currency_code": "QAR", "currency": "Qatari Riyal", "timezone": "Asia/Qatar"},
    "Romania": {"calling_code": "+40", "currency_code": "RON", "currency": "Romanian Leu", "timezone": "Europe/Bucharest"},
    "Russia": {"calling_code": "+7", "currency_code": "RUB", "currency": "Russian Ruble", "timezone": "Europe/Moscow"},
    "Saudi Arabia": {"calling_code": "+966", "currency_code": "SAR", "currency": "Saudi Riyal", "timezone": "Asia/Riyadh"},
    "Serbia": {"calling_code": "+381", "currency_code": "RSD", "currency": "Serbian Dinar", "timezone": "Europe/Belgrade"},
    "Singapore": {"calling_code": "+65", "currency_code": "SGD", "currency": "Singapore Dollar", "timezone": "Asia/Singapore"},
    "Slovakia": {"calling_code": "+421", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Bratislava"},
    "Slovenia": {"calling_code": "+386", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Ljubljana"},
    "South Africa": {"calling_code": "+27", "currency_code": "ZAR", "currency": "South African Rand", "timezone": "Africa/Johannesburg"},
    "South Korea": {"calling_code": "+82", "currency_code": "KRW", "currency": "South Korean Won", "timezone": "Asia/Seoul"},
    "Spain": {"calling_code": "+34", "currency_code": "EUR", "currency": "Euro", "timezone": "Europe/Madrid"},
    "Sri Lanka": {"calling_code": "+94", "currency_code": "LKR", "currency": "Sri Lankan Rupee", "timezone": "Asia/Colombo"},
    "Sweden": {"calling_code": "+46", "currency_code": "SEK", "currency": "Swedish Krona", "timezone": "Europe/Stockholm"},
    "Switzerland": {"calling_code": "+41", "currency_code": "CHF", "currency": "Swiss Franc", "timezone": "Europe/Zurich"},
    "Taiwan": {"calling_code": "+886", "currency_code": "TWD", "currency": "New Taiwan Dollar", "timezone": "Asia/Taipei"},
    "Thailand": {"calling_code": "+66", "currency_code": "THB", "currency": "Thai Baht", "timezone": "Asia/Bangkok"},
    "Turkey": {"calling_code": "+90", "currency_code": "TRY", "currency": "Turkish Lira", "timezone": "Europe/Istanbul"},
    "Uganda": {"calling_code": "+256", "currency_code": "UGX", "currency": "Ugandan Shilling", "timezone": "Africa/Kampala"},
    "Ukraine": {"calling_code": "+380", "currency_code": "UAH", "currency": "Ukrainian Hryvnia", "timezone": "Europe/Kiev"},
    "United Arab Emirates": {"calling_code": "+971", "currency_code": "AED", "currency": "UAE Dirham", "timezone": "Asia/Dubai"},
    "United Kingdom": {"calling_code": "+44", "currency_code": "GBP", "currency": "Pound Sterling", "timezone": "Europe/London"},
    "United States": {"calling_code": "+1", "currency_code": "USD", "currency": "United States Dollar", "timezone": "America/New_York"},
    "Uruguay": {"calling_code": "+598", "currency_code": "UYU", "currency": "Uruguayan Peso", "timezone": "America/Montevideo"},
    "Venezuela": {"calling_code": "+58", "currency_code": "VES", "currency": "Venezuelan Bolívar", "timezone": "America/Caracas"},
    "Vietnam": {"calling_code": "+84", "currency_code": "VND", "currency": "Vietnamese Dong", "timezone": "Asia/Ho_Chi_Minh"},
    "Zambia": {"calling_code": "+260", "currency_code": "ZMW", "currency": "Zambian Kwacha", "timezone": "Africa/Lusaka"},
    "Zimbabwe": {"calling_code": "+263", "currency_code": "ZWL", "currency": "Zimbabwean Dollar", "timezone": "Africa/Harare"},
}

# --- Product Pricing Database ---
PRODUCT_PRICES = {
    "ALEXANDRITE": {
        "min_price_per_carat": 60000,
        "max_price_per_carat": "60000+",
        "notes": "Indian origin: 25000-350000"
    },
    "ALEXANDRITE CATS EYE": {
        "min_price_per_carat": 60000,
        "max_price_per_carat": "60000+"
    },
    "AMETHYST": {
        "min_price_per_carat": 380,
        "max_price_per_carat": 13000
    },
    "AUSTRALIAN OPAL": {
        "min_price_per_carat": 150,
        "max_price_per_carat": 7000,
        "notes": "High-end play-of-color higher"
    },
    "BLUE SAPPHIRE": {
        "min_price_per_carat": 25000,
        "max_price_per_carat": "50000+",
        "notes": "Kashmir/Burmese origins command premium"
    },
    "BLUE SAPPHIRE (NEELAM)": {
        "min_price_per_carat": 25000,
        "max_price_per_carat": "50000+",
        "notes": "Kashmir/Burmese origins command premium"
    },
    "COLOMBIAN EMERALD": {
        "min_price_per_carat": 1155277,
        "max_price_per_carat": 1155277,
        "notes": "Converted from USD 13,919/ct"
    },
    "CULTURED PEARLS": {
        "min_price_per_carat": 1000,
        "max_price_per_carat": "20000+",
        "notes": "South Sea / Tahitian / Basra origins higher"
    },
    "EMERALD": {
        "min_price_per_carat": 1000,
        "max_price_per_carat": 437000,
        "notes": "Persian Emerald command higher price"
    },
    "EMERALD (PANNA)": {
        "min_price_per_carat": 1000,
        "max_price_per_carat": 437000,
        "notes": "Persian Emerald command higher price"
    },
    "OPAL": {
        "min_price_per_carat": 150,
        "max_price_per_carat": 7000,
        "notes": "Ethiopian opal: 1000-4000/ct"
    },
    "PERIDOT": {
        "min_price_per_carat": 664,
        "max_price_per_carat": 29216,
        "notes": "Converted from USD $8-$352"
    },
    "RED CORAL": {
        "min_price_per_carat": 1000,
        "max_price_per_carat": 5000
    },
    "RED CORAL (MOONGA)": {
        "min_price_per_carat": 1000,
        "max_price_per_carat": 5000
    },
    "RUBY": {
        "min_price_per_carat": 50000,
        "max_price_per_carat": 500000
    },
    "RUBY (MANIK)": {
        "min_price_per_carat": 50000,
        "max_price_per_carat": 500000
    },
    "SPESSARTITE": {
        "min_price_per_carat": 2739,
        "max_price_per_carat": 16434,
        "notes": "Converted from USD $33-$198"
    },
    "TANZANITE": {
        "min_price_per_carat": 1162,
        "max_price_per_carat": 68475,
        "notes": "Converted from USD $14-$825"
    },
    "YELLOW SAPPHIRE": {
        "min_price_per_carat": 2500,
        "max_price_per_carat": 40000
    },
    "YELLOW SAPPHIRE (PUKHRAJ)": {
        "min_price_per_carat": 2500,
        "max_price_per_carat": 40000
    },
    "ZAMBIAN EMERALD": {
        "min_price_per_carat": 2500,
        "max_price_per_carat": 40000
    }
}

# --- Currency Conversion Rates (INR to other currencies) ---
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
    "INR": 1.0, "CZK": 0.2682, "GTQ": 0.1008, "NIC": 0.4788, "PYG": 92.4374,
    "TND": 0.0378, "UZS": 157.3078, "MGA": 57.8432, "MUR": 0.6002,
    "XOF": 7.2478, "AOA": 11.9498
}

# --- Currency conversion function ---
def convert_inr_to_currency(inr_amount, target_currency_code):
    """Convert INR amount to target currency"""
    if target_currency_code == "INR":
        return inr_amount
    
    rate = INR_TO_CURRENCY.get(target_currency_code, INR_TO_CURRENCY["USD"])
    converted = inr_amount * rate
    return round(converted, 2)


def get_product_price_info(gemstone_name, currency_code="INR"):
    """Get product pricing information with currency conversion"""
    gemstone_upper = gemstone_name.upper().strip()
    
    # Try exact match first
    if gemstone_upper in PRODUCT_PRICES:
        product = PRODUCT_PRICES[gemstone_upper]
    else:
        # Try partial match
        found = None
        for key in PRODUCT_PRICES.keys():
            if gemstone_upper in key or key in gemstone_upper:
                found = key
                break
        
        if not found:
            return None
        
        product = PRODUCT_PRICES[found]
        gemstone_upper = found
    
    min_price = product["min_price_per_carat"]
    max_price = product["max_price_per_carat"]
    notes = product.get("notes", "")
    
    # Convert prices to target currency
    if currency_code != "INR":
        if isinstance(min_price, (int, float)):
            min_price_converted = convert_inr_to_currency(min_price, currency_code)
        else:
            min_price_converted = min_price
        
        if isinstance(max_price, (int, float)):
            max_price_converted = convert_inr_to_currency(max_price, currency_code)
        else:
            max_price_converted = max_price
        
        return {
            "gemstone": gemstone_upper,
            "min_price": min_price_converted,
            "max_price": max_price_converted,
            "currency": currency_code,
            "original_min_inr": min_price,
            "original_max_inr": max_price,
            "notes": notes
        }
    else:
        return {
            "gemstone": gemstone_upper,
            "min_price": min_price,
            "max_price": max_price,
            "currency": "INR",
            "notes": notes
        }


def format_price_range(price_info):
    """Format price range nicely for display"""
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
    
    if currency != "INR":
        result += f"\n(Converted from INR {price_info['original_min_inr']:,.0f}"
        if isinstance(price_info['original_max_inr'], str):
            result += "+"
        else:
            result += f" - {price_info['original_max_inr']:,.0f}"
        result += " per carat)"
    
    return result


# --- Timezone & Business Hours Functions ---
def get_business_hours_status(customer_timezone_str):
    """
    Check if current time in customer's timezone falls within IST business hours.
    Returns status with information CONVERTED to customer's local timezone.
    """
    try:
        # Get current time in customer's timezone
        customer_tz = pytz_timezone(customer_timezone_str)
        customer_now = dt.now(customer_tz)
        
        # Get current time in IST (business timezone)
        business_tz = pytz_timezone(BUSINESS_TIMEZONE)
        business_now = dt.now(business_tz)
        
        # Check if current day is a business day
        is_business_day = business_now.weekday() in BUSINESS_DAYS
        
        # Check if current time is within business hours
        current_hour = business_now.hour
        is_business_hours = (BUSINESS_START_HOUR <= current_hour < BUSINESS_END_HOUR)
        
        # Determine status
        is_within_hours = is_business_day and is_business_hours
        
        # Calculate business hours in CUSTOMER'S timezone
        customer_business_hours = get_business_hours_in_customer_tz(customer_tz, business_tz)
        customer_next_open = get_next_business_opening_customer_tz(business_now, customer_tz, business_tz)
        
        return {
            "is_within_business_hours": is_within_hours,
            "customer_local_time": customer_now.strftime("%I:%M %p"),
            "customer_date": customer_now.strftime("%A, %B %d, %Y"),
            "customer_timezone": customer_timezone_str,
            "customer_business_hours": customer_business_hours,
            "customer_next_business_opens": customer_next_open,
            "business_time_ist": business_now.strftime("%I:%M %p IST"),
            "business_date_ist": business_now.strftime("%A, %B %d, %Y"),
            "is_business_day": is_business_day
        }
    except Exception as e:
        logger.error(f"get_business_hours_status() error: {e}")
        return {
            "is_within_business_hours": True,  # Default to True to avoid blocking
            "customer_local_time": "Unknown",
            "customer_date": "Unknown",
            "customer_timezone": customer_timezone_str,
            "customer_business_hours": "Monday-Friday, 9 AM - 6 PM",
            "customer_next_business_opens": "during business hours",
            "business_time_ist": "Unknown",
            "error": str(e)
        }


def get_business_hours_in_customer_tz(customer_tz, business_tz):
    """
    Convert IST business hours to customer's local timezone.
    Returns a formatted string like "Monday-Friday, 5:30 AM - 2:30 PM"
    """
    try:
        # Create a sample business day in IST
        sample_date = dt.now(business_tz).replace(hour=BUSINESS_START_HOUR, minute=0, second=0, microsecond=0)
        
        # Create start and end times in IST
        start_time_ist = sample_date.replace(hour=BUSINESS_START_HOUR)
        end_time_ist = sample_date.replace(hour=BUSINESS_END_HOUR)
        
        # Convert to customer's timezone
        start_time_customer = start_time_ist.astimezone(customer_tz)
        end_time_customer = end_time_ist.astimezone(customer_tz)
        
        # Format the times
        start_str = start_time_customer.strftime("%I:%M %p").lstrip("0")
        end_str = end_time_customer.strftime("%I:%M %p").lstrip("0")
        
        # Handle day changes
        if start_time_customer.date() != end_time_customer.date():
            # Business hours span across days for customer
            return f"Monday-Friday, {start_str} - {end_str} (next day) your local time"
        else:
            return f"Monday-Friday, {start_str} - {end_str} your local time"
    except Exception as e:
        logger.error(f"get_business_hours_in_customer_tz() error: {e}")
        return "Monday-Friday, 9 AM - 6 PM IST"


def get_next_business_opening_customer_tz(business_now, customer_tz, business_tz):
    """
    Calculate when business hours will next open, displayed in CUSTOMER'S local time.
    """
    try:
        current_hour = business_now.hour
        current_day = business_now.weekday()
        
        # If it's during business hours today
        if current_day in BUSINESS_DAYS and current_hour < BUSINESS_END_HOUR:
            if current_hour < BUSINESS_START_HOUR:
                # Before opening today - calculate opening time
                next_open_ist = business_now.replace(hour=BUSINESS_START_HOUR, minute=0, second=0, microsecond=0)
                next_open_customer = next_open_ist.astimezone(customer_tz)
                
                # Check if it's today or tomorrow for customer
                customer_now = dt.now(customer_tz)
                if next_open_customer.date() == customer_now.date():
                    return f"today at {next_open_customer.strftime('%I:%M %p').lstrip('0')}"
                elif next_open_customer.date() == (customer_now + datetime.timedelta(days=1)).date():
                    return f"tomorrow at {next_open_customer.strftime('%I:%M %p').lstrip('0')}"
                else:
                    return f"{next_open_customer.strftime('%A')} at {next_open_customer.strftime('%I:%M %p').lstrip('0')}"
            else:
                # Currently open
                return "now (currently open)"
        
        # Find next business day
        days_until_next = 1
        next_day = (current_day + 1) % 7
        
        while next_day not in BUSINESS_DAYS:
            days_until_next += 1
            next_day = (current_day + days_until_next) % 7
        
        # Calculate next opening time in IST
        next_open_ist = business_now + datetime.timedelta(days=days_until_next)
        next_open_ist = next_open_ist.replace(hour=BUSINESS_START_HOUR, minute=0, second=0, microsecond=0)
        
        # Convert to customer timezone
        next_open_customer = next_open_ist.astimezone(customer_tz)
        customer_now = dt.now(customer_tz)
        
        # Determine relative day name
        days_diff = (next_open_customer.date() - customer_now.date()).days
        
        if days_diff == 0:
            day_str = "today"
        elif days_diff == 1:
            day_str = "tomorrow"
        else:
            day_str = next_open_customer.strftime('%A')
        
        time_str = next_open_customer.strftime('%I:%M %p').lstrip('0')
        
        return f"{day_str} at {time_str}"
        
    except Exception as e:
        logger.error(f"get_next_business_opening_customer_tz() error: {e}")
        return "during business hours (Mon-Fri, 9 AM - 6 PM IST)"


def format_business_hours_message(hours_status, is_urgent=False):
    """Format a friendly message about business hours status - tailored to customer's timezone"""
    if hours_status.get("is_within_business_hours"):
        return None  # No message needed, proceed normally
    
    # Outside business hours - show in CUSTOMER'S local time
    customer_time = hours_status.get("customer_local_time", "Unknown")
    customer_next_open = hours_status.get("customer_next_business_opens", "during our business hours")
    customer_hours = hours_status.get("customer_business_hours", "Monday-Friday, 9 AM - 6 PM your local time")
    
    if is_urgent:
        return (
            f"🕐 Thank you for reaching out! I notice it's currently {customer_time} in your timezone.\n\n"
            f"While I can assist you right now with product information and answer questions, "
            f"our team will be available for direct consultation {customer_next_open}.\n\n"
            f"Feel free to continue, and our expert team will follow up during business hours if needed!"
        )
    else:
        return (
            f"🕐 Thank you for your message! It's currently {customer_time} in your timezone.\n\n"
            f"Our business hours are {customer_hours}.\n"
            f"Our team will be available {customer_next_open}.\n\n"
            f"I can still help you with information right now, or you can expect a response from our team during business hours. How can I assist you?"
        )


# --- Prompts ---
SYSTEM_PROMPT = '''You are a lead qualifier at GemPundit.com and not the gem advisor, India's leading online store for loose gemstones and gemstone jewellery both for an astrological purpose as well as for a jewellery purpose. You need to ensure you disqualify leads that are not sales-oriented so they don't waste the gemstone expert's time. As a brand our mission is to simplify the complexity of buying colored gemstones, and celebrate and spread the wonder of colored gemstones to the world. Our brand personality is Capable, Helpful, Principled, Cultured and Creative, and this must reflect in your communication. Our values are to Celebrate the beauty and healing properties of gemstones, genuine care for our customers, respect and compassion, Integrity and to think big, and our communication needs to reflect that.
We want to ensure that the customer has an intent to buy a gemstone, and has clarity on what gemstone he wishes to buy. We must try to extract the weight (in either carats or ratti) that he is looking for of the gemstone (unless it's for a jewellery purpose), and try to extract the budget in a very savvy way, so it doesn't come across as very sales-ish. The intention with the budget is so that we can connect him to the gemstone expert who specializes in that budget range.

LANGUAGE LOCK
Support only English, Hindi (देवनागरी), and Hinglish.
Detect user's last message:
- Devanagari → reply in Hindi.
- Latin with Hinglish cues (kaise, kya, ji, ratti, pandit…) → Hinglish.
- Otherwise → English.
If another language appears → reply once in that language:
"Right now I can assist in English, Hindi, or Hinglish. Could we continue in one of these?"

#
PERSONALITY
Your name is Adolf Hitler and will work as the gempundit lead qualifier.
Always do a greeting "Hello, welcome to GemPundit." but should be done only once at the start of the conversation.
Warm, calm, respectful—like a human gem advisor, not a scripted bot.
Short, clear lines. One question at a time. Be curious and gentle and straight to the point.
Fastpace the chat naturally to understand the customer's intent and quick qualification of lead.
Values: celebrate beauty & healing properties; genuine care; respect & compassion; integrity; think big.
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
Avoid raising the customer's budget much if it's already good for eg"If the customer's budget is ₹1 lakh, we can try to gently encourage them to increase it to around ₹1.5 lakh. However, if we suggest raising their budget to ₹3–4 lakh right away, there's a high chance they might leave the conversation."
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
#

SMART SNIPPETS (GemPundit Blog)
If asked: how to wear / which finger / metal / day / energize / benefits / who should wear / side effects / meaning,
fetch from GemPundit blog using one link max.
Summarize in 2–3 short lines.
First line ends with the single raw GemPundit URL (no markdown).
Example:
"Amethyst is a calming stone often linked with Saturn and February births. https://www.gempundit.com/blog/how-to-wear-amethyst
Usually worn in silver on Saturday evenings. Want me to guide you on ring or pendant?"
If no relevant GemPundit page → summarize briefly in 2–3 lines (no link).

PRODUCT LINK BEHAVIOR
If the user sends a GemPundit URL:
- Scraper provides details (gemstone, weight, price, shape, origin, etc.).
- Confirm gently:
"Okay... you're looking at a {gemstone}, around {carat_or_ratti}. Shall I confirm if this piece suits your purpose?"
If price missing:
"I can't see the price on my end. Could you confirm what you see or share a quick screenshot?"
Save all scraped details to the database.

IMAGE HANDLING
If a customer shares an image of a gemstone:
First, politely acknowledge the image.
Identify the gemstone shown — for example: "This looks like a Blue Sapphire."
If it's a precious gemstone (Ruby, Emerald, Blue Sapphire, Yellow Sapphire, etc), mention it clearly.
Then, mention the popular substitute stones that are often worn in place of it is customer asks for it.
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
Always maintain a respectful, advisory tone — never dismiss substitutes directly.
Prioritize the astrologer step before showing gemstone options.
If the customer requests the astrologer link, provide:
https://www.gempundit.com/free-gemstone-recommendation
Keep each message short and human-like (2–3 lines).
Avoid using emojis or decorative language in this flow.
Log substitute mention and mapped main gemstone to the lead database.

CORNER CASE
If customer sends a image of a jewellery then you may not ask the use case of customer as it is already a jewellery.
If a customer talks about talking to a person and not a bot more than once, you can generate him a ticket number and mark his lead as executive required.
Unless Customer asks for certification don't tell him anything about it.
When you ask use case astrological or jewellery and user replies yes, mark it as use for astrological.  ######
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
Ff user asks for astrologer, you must ask for date of birth, place of birth and time of birth.
if user says like "Hi, I've seen a sunset Padpardscha cushion 2.04 carats Can you please tell me its price" ask for SKU number, if i's mentioned as call for price, kindly reply it's very hard to tell the exact price, We can connect you to our gemstone expert.
If someone asks for authencity of a stone then reply back With all the gemstones we do provide government authorized lab certificate from our end which you can verify online at your convienience.
If someone asks for ring designs then reply back With we have Our in-house craftmanship and designs, Custom designs are also accepted, and we share CAD previews before making.
If price is recieved by you via url scraper, mark it as a rough budget and skip to next question.
Do not state any other price. Just keep the one from the url as the onlt price.
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
1. Was only looking for a free gemstone recommendation with no serious intent of buying (in which case we politely nudge him to our free online gem recommendation tool at https://gempundit.com/gem-recommendation and/or urge him to buy a paid consultation with our astrologer of Rs 2100 on which we can give him a discount upto 50% as deemed necessary): https://www.gempundit.com/products/astro-phone-consultation. We can also pitch a 15 min free consultation with our astrologer if he seems to be looking at a precious gemstone or a budget of INR 20k or higher
2. The gemstone budget is estimated to be below Rs 10000 (either explicitly stated, or perceived if gemstone is a typical low value semi-precious gemstone). In which case we will double check if he is willing to raise his budget to explore better options (if the gemstone typically has options in higher price points as well) and try to help him ourself as much as we can, but nudge him to explore the website which has all the ecommerce features (take them for granted)
3. The person is actually looking to sell gemstones to us (in which case  we ask him to rather reach out to procurement@gempundit.com)
4. The person is looking for a job with our company and not to buy a gemstone! (in which case we ask him to reach out to career@gempundit.com)
5. Its not a product related to gems and jewellery. In which case, we politely inform and stop responding to the conversation
6. The person is looking to get an appraisal for an item that they already own (be on the watch out for cases where the customer is very particular and looking for the exact carat weight of a gemstone in 2 decimal places, like say 4.23 carat sapphire - since usually no one has such specific requirements, there is a high likelihood that he has a gemstone weighing that much and simply is trying to see comparative gemstones and their price. And hence, the customer should be specifically probed whether this is a gemstone they are looking to sell or appraise, as the request seems surprising. Note that the exception to this is when a customer asks this in ratti (1 ratti = 0.9 carats) and there specific requests are ok, as they typically come from an astrologer like 5.25 ratti)
7. The person shares an obviously fake email address like hello@gmail.com - You must evaluate whether it is likely a valid, genuine email address owned by the user or it might be misleading or incorrect. Analyze the structure, domain, and other relevant factors of the email address. Be very conservative and figure out the probability of that not being incorrect or misleading, if there is more than a 30% chance of it being incorrect or misleading, ask the user to review the email address again or provide an alternate email address. If you are unable to get an email address that passes this criterion, mark the conversation as 'Send to Manual Review Team before Qualification'
8. When the customer is based out of one of the non-serviceable countries (Pakistan, Iran, Russia). however, in this case, we will typically never ask them where they will need the shipment unless we have specific reason to believe that it could be one of these countries.
9. When the customer is a reseller, and would only purchase after physically reviewing the item, but is not willing to come to our gurgaon  office to visit and provide the url https://www.gempundit.com/contact-us.
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

For your reference, Today's Date is: "&text(today(),"dd, MMM, YYYY")&"

{{context}}

RULES:
- Always translate the answer that you want to give in the language of the last message that the user sends.
- Always be truthful and never say something that is not based on the real information from the context.
- The context in JSON array should never by sent to the user. The context should only be used to answer the questions
- Never mention that information is based on a context"

ESSENCE
Be a human gem guide — calm, kind, insightful.
Understand why they're drawn to the stone, not just what they want.
Keep it personal, one question at a time.
End warmly, never robotic.
'''

current_date = datetime.datetime.now().strftime("%d, %b, %Y")
SYSTEM_PROMPT = SYSTEM_PROMPT.replace('Today\'s Date is: "&text(today(),"dd, MMM, YYYY")&"', f"Today's Date is: {current_date}")


# Add budget escalation and contact info to system prompt
BUDGET_ESCALATION_RULES = """

🔄 BUDGET ESCALATION PROTOCOL:
When customer mentions budget is lower than product price OR says "can't afford" or "too expensive":
1. DO NOT immediately disqualify
2. Ask: "Would you like one of our executives to call you to discuss options within your budget?"
3. If YES → Ask for preferred time slot (mention: Mon-Fri, 9 AM - 6 PM IST)
4. Collect: Name, Email, Phone, Preferred Date/Time
5. Generate JSON with "Qualification Decision": "Budget Escalation - Call Requested"
6. DO NOT show ticket number to customer
7. Response: "Thank you! Our executive will call you on [date/time] to discuss options."

📞 SALES DESK NUMBERS (when to provide):
Only provide phone numbers when:
- Customer explicitly asks for phone number / "how to contact" / "call you"
- Customer wants immediate assistance
- After budget escalation (if they prefer calling directly)

Provide based on location:
- India customers: +91 11 4084 4599 (India Sales Desk)
- UK/Europe customers: +44 20 3769 9131 (UK Sales Desk)  
- All others: +1 631 201 1254 (US Sales Desk)

Format: "You can reach our [Location] sales desk at [number]. Working hours: Monday-Friday, 9 AM - 6 PM IST."

🏢 GURGAON OFFICE ADDRESS (when to provide):
Only provide address when:
- Customer asks "where are you located" / "office address" / "want to visit"
- Customer says they want to visit physically

Address format:
"Our Gurgaon office:
Fortuna Retail Pvt. Ltd.
312-316, 3rd Floor, Vipul Agora
MG Road, Gurgaon, Haryana, 122002
Phone: +91 11 4084 4599

Please call ahead to schedule your visit. Working hours: Monday-Friday, 9 AM - 6 PM IST."

⚠ TICKET NUMBER DISPLAY RULE:
- NEVER show ticket number in customer-facing messages
- Exception: If customer explicitly asks "what is my ticket number" or "reference number"
- In JSON: Always include ticket ID for internal tracking
- Customer message: "Thank you! We've recorded your details and will follow up soon."
"""

SYSTEM_PROMPT = SYSTEM_PROMPT + BUDGET_ESCALATION_RULES

logger.info(f"📋 System prompt loaded ({len(SYSTEM_PROMPT)} chars)")

# --- History setup ---

# --- Runtime state ---

# --- Message Batching State ---
pending_messages = {}  # {phone: [list of message texts]}
last_msg_time = {}     # {phone: timestamp}
batch_timers = {}      # {phone: Timer object}
COMBINE_WINDOW = 10    # seconds

# --- Ping/Follow-up State ---
last_bot_response_time = {}  # {phone: timestamp}
ping_count = {}              # {phone: number of pings sent}
user_last_message_time = {}  # {phone: timestamp of last user message}
PING_SCHEDULE = [3*60, 8*60, 15*60]  # 3min, 8min, 15min
qualified_leads = set()
user_country_codes = {}
user_business_hours_notified = set()  # Track who has been notified about business hours


# --- URL Detection ---
SKU_RE = re.compile(r"\bGP\d{4,6}\b", re.I)
URL_RE = re.compile(r"https?://[^\s]+", re.I)


# === Helper Functions ===

def generate_ticket_id():
    """Generate ticket ID in format: GP-DDMMMYYYY-XXXXXX"""
    date_str = datetime.datetime.now().strftime("%d%b%Y").upper()
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"GP-{date_str}-{random_chars}"


def extract_country_code(phone_number: str) -> dict:
    """Extract country code and return country info with currency and timezone"""
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
        "387": "Bosnia and Herzegovina", "420": "Czech Republic", "421": "Slovakia", "501": "Belize",
        "503": "El Salvador", "506": "Costa Rica", "591": "Bolivia", "598": "Uruguay", "852": "Hong Kong",
        "855": "Cambodia", "856": "Laos", "880": "Bangladesh", "886": "Taiwan", "961": "Lebanon",
        "962": "Jordan", "964": "Iraq", "965": "Kuwait", "966": "Saudi Arabia", "968": "Oman",
        "971": "United Arab Emirates", "972": "Israel", "973": "Bahrain", "974": "Qatar",
        "977": "Nepal", "994": "Azerbaijan", "995": "Georgia"
    }
    
    for length in [3, 2, 1]:
        if len(phone) >= length:
            code = phone[:length]
            if code in country_codes:
                country_name = country_codes[code]
                remaining_number = phone[length:]
                formatted_phone = f"+{code}-{remaining_number}"
                
                # Get currency and timezone info
                country_data = COUNTRY_CURRENCY_MAP.get(country_name, {
                    "currency_code": "USD",
                    "currency": "United States Dollar",
                    "timezone": "UTC"
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
        "country_code": "Unknown",
        "country": "Unknown",
        "phone_number": phone,
        "formatted_phone": phone,
        "currency_code": "USD",
        "currency_name": "United States Dollar",
        "timezone": "UTC"
    }


def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe audio using OpenAI Whisper"""
    try:
        temp_path = f"logs/temp_audio_{uuid.uuid4()}.ogg"
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)
        
        with open(temp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        
        os.remove(temp_path)
        
        text = transcript.text.strip()
        logger.info(f"🎤 Transcribed audio: {text[:100]}...")
        return text
    except Exception as e:
        logger.error(f"transcribe_audio() error: {e}\n{traceback.format_exc()}")
        return None


def analyze_image(image_bytes: bytes) -> str:
    """Analyze image using GPT-4 Vision - specialized for gemstone images"""
    try:
        import base64
        
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """You are a gemstone expert analyzing customer images. Identify what type of image this is and provide relevant analysis:

*IMAGE CATEGORIES:*
1. *Gemstone in Ring/Jewelry* - If you see a ring, pendant, earring, or other jewelry
2. *Loose Gemstone* - Single gemstone without setting
3. *Gemstone in Palm/Hand* - Stone being held
4. *Raw/Rough Stone* - Uncut, natural crystal form
5. *Certificate/Documentation* - Lab certificate or gemstone papers
6. *Product Screenshot* - Screenshot from any website/online store showing product details
7. *Multiple Items* - Collection of gemstones or jewelry

*ANALYSIS TO PROVIDE:*

For ALL images, identify:
- Gemstone type (Ruby, Sapphire, Emerald, etc.) - be specific with varieties (e.g., "Blue Sapphire" not just "Sapphire")
- Color description (vivid blue, pigeon blood red, grass green, etc.)
- Approximate size/carat (if visible reference like finger, ruler, or stated)

For *Jewelry/Ring images*:
- Metal type (gold, silver, platinum - and color like yellow gold, white gold)
- Setting style (prong, bezel, halo, solitaire, etc.)
- Overall design quality
- Whether it looks custom/handmade or mass-produced

For *Loose Gemstones*:
- Cut/shape (round, oval, cushion, emerald cut, etc.)
- Faceting quality
- Clarity observations (inclusions visible?)
- Luster/brilliance

For *Raw/Rough Stones*:
- Natural crystal form
- Whether it appears genuine or treated
- Mining quality indicators

For *Product Screenshots* (from any website):
- Extract: gemstone type, weight (carats), price shown, any specifications
- **CRITICAL**: NEVER mention "competitor" or "another store" to customer
- Say: "I can see you're interested in this [gemstone]. Let me help you find it at GemPundit!"
- Use extracted details to show them matching products

For *Certificates*:
- Lab name (GIA, IGI, GRS, etc.)
- Gemstone details mentioned
- Certificate number if visible
- Treatment information

*IMPORTANT INSTRUCTIONS:*
- Be honest if you cannot identify something clearly
- For product screenshot images: extract ALL visible details (price, weight, specifications)
- Always mention if the gemstone appears natural or treated
- If quality looks poor/fake, say "appears to be low quality" diplomatically
- Estimate value range ONLY if clearly identifiable and high-quality

Format your response clearly with relevant details only."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=800
        )
        
        analysis = response.choices[0].message.content.strip()
        logger.info(f"🖼 Image analyzed: {analysis[:150]}...")
        return analysis
        
    except Exception as e:
        logger.error(f"analyze_image() error: {e}\n{traceback.format_exc()}")
        return None


def extract_json_blocks(text):
    """Extracts valid JSON objects safely"""
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
    """Save structured lead info to leads.jsonl"""
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "phone": phone,
        "lead_data": data
    }
    with open(LEAD_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.info(f"🧾 Lead logged for {phone}: {json.dumps(data, ensure_ascii=False)}")




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
    """Extract product details - merged price3 logic with per-carat support"""
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

    call_for_price_text = (
        "This is an exclusive and rare category of the gemstone. "
        "The price for this category starts from USD 30,000. "
        "Please share your contact details and our Padparadscha expert will call you to share the exact price."
    )

    if call_for_price_text in page_text or "starts from USD 30,000" in page_text:
        out["price"] = "Call for Price"
        out["is_call_for_price"] = True
        logger.info("🔍 Detected 'Call for Price' product using exact text match")
    else:
        is_per_carat = False
        lowered = page_text.lower()
        if "per carat" in lowered or "/carat" in lowered:
            is_per_carat = True
            logger.info("🔍 Detected 'per carat' pricing indicator")

        price_meta = soup.select_one('meta[itemprop="price"]')
        if price_meta and price_meta.get("content"):
            price_raw = re.sub(r"[^\d.]", "", price_meta["content"])
            price_raw = price_raw.strip(".")
            if price_raw and price_raw.replace(".", "").isdigit():
                out["price"] = price_raw
                if is_per_carat:
                    out["is_per_carat_price"] = True
                    logger.info(f"💰 Price {price_raw} is PER CARAT (not total)")
        else:
            price_text = ""
            for sel in [".price", ".final-price", ".product-price", "[data-price-amount]"]:
                n = soup.select_one(sel)
                if n:
                    price_text = n.get("data-price-amount") or n.get_text(" ", strip=True)
                    break
            if price_text:
                digits = re.sub(r"[^\d.]", "", price_text)
                digits = digits.strip(".")
                if digits and digits.replace(".", "").isdigit():
                    out["price"] = digits
                    if is_per_carat:
                        out["is_per_carat_price"] = True
                        logger.info(f"💰 Price {digits} is PER CARAT (not total)")

    cur_meta = soup.select_one('meta[itemprop="priceCurrency"]')
    if cur_meta and cur_meta.get("content"):
        out["currency"] = cur_meta["content"]
    else:
        out["currency"] = "INR"

    avail = soup.select_one('link[itemprop="availability"]')
    if avail and avail.get("href"):
        out["availability"] = avail["href"]

    spec_text = page_text

    m = re.search(r"(\d+(\.\d+)?)\s*(carat|ct|ratti)s?\b", spec_text, re.I)
    if m:
        out["carat"] = m.group(1)
        if "ratti" in m.group(3).lower():
            out["unit"] = "ratti"
        else:
            out["unit"] = "carat"

    weight_pattern = re.compile(r"WEIGHT[^:]*:\s*([^-]+)", re.I)
    weight_match = weight_pattern.search(spec_text)
    if weight_match and not out.get("carat"):
        weight_text = weight_match.group(1).strip()
        weight_num = re.search(r"(\d+(\.\d+)?)", weight_text)
        if weight_num:
            out["carat"] = weight_num.group(1)
            if "ratti" in weight_text.lower():
                out["unit"] = "ratti"
            else:
                out["unit"] = "carat"

    m = re.search(r"\bOrigin\s*[:\-]\s*([A-Za-z\s()]+)", spec_text, re.I)
    if m:
        out["origin"] = m.group(1).strip()

    m = re.search(r"\bColor\s*[:\-]\s*([A-Za-z\s()]+)", spec_text, re.I)
    if m:
        out["color"] = m.group(1).strip()

    m = re.search(r"\bShape\s*[:\-]\s*([A-Za-z\s()]+)", spec_text, re.I)
    if m:
        out["shape"] = m.group(1).strip()
    else:
        for sh in ["Oval", "Round", "Pear", "Cushion", "Emerald", "Princess", "Radiant", "Cabochon", "Heart"]:
            if re.search(rf"\b{sh}\b", spec_text, re.I):
                out["shape"] = sh
                break

    m = re.search(r"\bTreatment\s*[:\-]\s*([A-Za-z\s()]+)", spec_text, re.I)
    if m:
        out["treatment"] = m.group(1).strip()
    else:
        if re.search(r"\b(Unheated|No Heat)\b", spec_text, re.I):
            out["treatment"] = "Unheated"
        elif re.search(r"\b(Heated|Heat Treatment)\b", spec_text, re.I):
            out["treatment"] = "Heated"

    gemstone_keywords = [
        "Blue Sapphire", "Yellow Sapphire", "Pink Sapphire", "White Sapphire",
        "Ruby", "Emerald", "Pearl", "Coral", "Hessonite", "Cat's Eye",
        "Diamond", "Opal", "Amethyst", "Citrine", "Topaz", "Garnet",
        "Peridot", "Aquamarine", "Sapphire"
    ]

    name_text = out.get("name", "").lower()
    for gem in gemstone_keywords:
        if gem.lower() in name_text:
            out["gemstone"] = gem
            break

    if "gemstone" not in out:
        search_text = (out.get("name", "") + " " + spec_text).lower()
        for gem in gemstone_keywords:
            if gem.lower() in search_text:
                out["gemstone"] = gem
                break

    cert_block = None
    for sel in ["#certificate", ".certificate", ".certification", "[name='certificate']"]:
        n = soup.select_one(sel)
        if n:
            cert_block = n.get_text(" ", strip=True)
            break
    if cert_block:
        out["certification"] = cert_block

    return out


def parse_category(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out = {"url": url, "type": "category"}

    cat = None
    h1 = soup.select_one("h1, .page-title")
    if h1:
        cat = h1.get_text(strip=True)
    if not cat and soup.title:
        cat = soup.title.get_text(strip=True)
    if cat:
        out["category_name"] = cat
        
        gemstone_keywords = ["Ruby", "Sapphire", "Emerald", "Pearl", "Coral", "Yellow Sapphire", 
                             "Blue Sapphire", "Hessonite", "Cat's Eye", "Diamond", "Opal"]
        for gem in gemstone_keywords:
            if gem.lower() in cat.lower():
                out["gemstone"] = gem
                break

    return out


def scrape_url(url: str) -> dict:
    """Main scraping function"""
    try:
        logger.info(f"🔍 Scraping URL: {url}")

        # Check for checkout/cart URL
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
            result = parse_product(html, url)
            logger.info(f"📦 Product scraped: {result.get('name', 'Unknown')}")
            return result
        elif is_category_url(url):
            result = parse_category(html, url)
            logger.info(f"📂 Category scraped: {result.get('category_name', 'Unknown')}")
            return result
        else:
            return {"error": "Unknown GemPundit page type"}
            
    except Exception as e:
        logger.error(f"scrape_url() error: {e}\n{traceback.format_exc()}")
        return {"error": str(e)}


def format_scraped_data(data: dict, currency_code: str = "USD") -> str:
    """Format scraped data for GPT context with currency conversion"""
    if data.get("error"):
        if data.get("error") == "cart_url_private":
            return f"[CART URL DETECTED - PRIVATE]\n{data.get('message', 'Cannot access cart URL')}"
        return f"[URL Scraping Error: {data['error']}]"

    
    if data.get("type") == "product":
        parts = ["[PRODUCT DETAILS FROM URL - USER IS VIEWING THIS SPECIFIC PRODUCT]"]
        parts.append("IMPORTANT: Customer is looking at THIS EXACT product. Confirm the details and ask if they want to proceed.")
        parts.append("")
        if data.get("name"):
            parts.append(f"Product Name: {data['name']}")
        if data.get("gemstone"):
            parts.append(f"Gemstone Type: {data['gemstone']}")
        if data.get("sku"):
            parts.append(f"SKU/Product Code: {data['sku']}")
        if data.get("carat"):
            unit = data.get("unit", "carat")
            parts.append(f"Weight: {data['carat']} {unit}")
        if data.get("shape"):
            parts.append(f"Shape/Cut: {data['shape']}")
        if data.get("color"):
            parts.append(f"Color: {data['color']}")
        if data.get("origin"):
            parts.append(f"Origin: {data['origin']}")
        if data.get("treatment"):
            parts.append(f"Treatment: {data['treatment']}")
        if data.get("certification"):
            parts.append(f"Certification / Lab Report: {data['certification']}")
        
        if data.get("is_call_for_price"):
            parts.append("Price: Call for Price (Premium/High-value gemstone)")
        elif data.get("price"):
            original_currency = data.get("currency", "INR")
            price_value = data["price"]
            
            if data.get("is_per_carat_price"):
                parts.append(f"Price per Carat: {original_currency} {price_value}")
                parts.append("⚠️ IMPORTANT: This is the PER CARAT price, NOT the total price!")
                
                if data.get("carat"):
                    try:
                        carat_weight = float(str(data["carat"]).replace(",", ""))
                        price_float = float(str(price_value).replace(",", ""))
                        total_price = carat_weight * price_float
                        parts.append(f"Total Price: {original_currency} {total_price:,.0f} (for {carat_weight} carat)")
                        parts.append("IMPORTANT: When discussing with customer, mention BOTH per carat AND total price.")
                    except Exception:
                        pass
            else:
                parts.append(f"Total Price: {original_currency} {price_value}")
            
            parts.append(f"IMPORTANT: Convert prices to {currency_code} when discussing with customer")
        
        parts.append("")
        parts.append("RESPONSE INSTRUCTION:")
        parts.append("1. Acknowledge: 'I can see you're viewing [gemstone name] - [weight] carat'")
        parts.append("2. Confirm details: Briefly mention 1-2 key features (origin, treatment, or color)")
        parts.append(f"3. Quote price in {currency_code} (converted from {data.get('currency', 'INR')})")
        if data.get("is_per_carat_price") and data.get("carat"):
            parts.append("4. CRITICAL: Mention BOTH per-carat price AND total price clearly")
            parts.append("   Example: 'The price is [X] per carat, so for [Y] carat the total is [Z]'")
            parts.append("5. Ask ONLY: 'Would you like to proceed with this gemstone, or would you like to see similar options?'")
            parts.append("6. DO NOT ask about weight/carat - it's already specified!")
            parts.append("7. DO NOT ask which gemstone - they're viewing a specific product!")
        else:
            parts.append("4. Ask ONLY: 'Would you like to proceed with this gemstone, or would you like to see similar options?'")
            parts.append("5. DO NOT ask about weight/carat - it's already specified!")
            parts.append("6. DO NOT ask which gemstone - they're viewing a specific product!")
        
        return "\n".join(parts)
    
    elif data.get("type") == "category":
        parts = ["[CATEGORY PAGE DETAILS FROM URL]"]
        if data.get("category_name"):
            parts.append(f"Category Name: {data['category_name']}")
        if data.get("gemstone"):
            parts.append(f"Gemstone Type: {data['gemstone']}")
        
        parts.append("")
        parts.append("RESPONSE INSTRUCTION:")
        parts.append("1. Recognize that user is browsing a general gemstone category (not a specific stone).")
        parts.append("2. Ask about their specific requirements: gemstone purpose, carat/weight range, budget in their currency, and preferred origin/quality if relevant.")
        parts.append("3. Use pricing database to give a rough per-carat range in their currency.")
        parts.append("4. Then ask if they'd like to see matching options.")
        
        return "\n".join(parts)
    
    else:
        return "[URL Scraping: Unrecognized data structure]"


def call_openai_with_websearch(user_text: str, context: list, scraped_data: dict = None, phone: str = None):
    """Call OpenAI API with context and optional scraped data"""
    try:
        logger.info(f"🧠 Calling GPT ({OPENAI_MODEL}) for: {user_text[:100]}")
        
        currency_code = "USD"
        currency_name = "United States Dollar"
        customer_timezone = "UTC"
        
        if phone and phone in user_country_codes:
            currency_code = user_country_codes[phone].get("currency_code", "USD")
            currency_name = user_country_codes[phone].get("currency_name", "United States Dollar")
            customer_timezone = user_country_codes[phone].get("timezone", "UTC")
        
        price_query_keywords = ["price", "cost", "how much", "pricing", "rate", "charges"]
        is_price_query = any(keyword in user_text.lower() for keyword in price_query_keywords)
        
        gemstone_mentioned = None
        for gemstone in PRODUCT_PRICES.keys():
            if gemstone.lower() in user_text.lower():
                gemstone_mentioned = gemstone
                break
        
        enhanced_user_text = user_text
        
        if is_price_query and gemstone_mentioned:
            price_info = get_product_price_info(gemstone_mentioned, currency_code)
            if price_info:
                formatted_price = format_price_range(price_info)
                enhanced_user_text = f"{user_text}\n\n[PRODUCT PRICING INFO]\n{formatted_price}"
                logger.info(f"💰 Added pricing info for {gemstone_mentioned} in {currency_code}")
        
        if scraped_data and not scraped_data.get("error"):
            formatted_data = format_scraped_data(scraped_data, currency_code)
            enhanced_user_text = f"{enhanced_user_text}\n\n{formatted_data}"
            logger.info(f"📎 Appended scraped data with currency {currency_code}")
        
        # Get business hours status
        hours_status = get_business_hours_status(customer_timezone)
        
        # Add timezone and business hours context
        time_context = f"""

🕐 CUSTOMER TIMEZONE & BUSINESS HOURS INFORMATION:
Customer's Local Time: {hours_status['customer_local_time']} ({hours_status['customer_date']})
Customer Timezone: {customer_timezone}
Business Time (IST): {hours_status['business_time_ist']} ({hours_status.get('business_date_ist', 'N/A')})
Business Hours: Monday-Friday, 9 AM - 6 PM IST
Currently Within Business Hours: {'YES - Can connect immediately' if hours_status['is_within_business_hours'] else f"NO - Next opening: {hours_status.get('next_business_opens', 'Unknown')}"}

BUSINESS HOURS HANDLING INSTRUCTIONS:
{'✅ IMMEDIATE CONNECTION: Customer is messaging during business hours. Proceed normally with lead qualification and inform them our team is available now for immediate assistance.' if hours_status['is_within_business_hours'] else f"⏰ OUTSIDE BUSINESS HOURS: Customer is messaging outside business hours. You should still help them with information and qualification, but inform them that our expert team will be available {hours_status.get('next_business_opens', 'during business hours')} for direct consultation or follow-up."}

When appropriate in the conversation, naturally mention:
- {'Our team is currently available and can assist you right away!' if hours_status['is_within_business_hours'] else f"Our team will be available {hours_status.get('next_business_opens', 'during business hours')} to follow up with you."}
- Do NOT block the conversation - always provide helpful information regardless of business hours
- If customer seems urgent/ready to buy: {'Connect them immediately with the team' if hours_status['is_within_business_hours'] else 'Take their details and assure follow-up during business hours'}
"""
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *context,
            {"role": "user", "content": enhanced_user_text}
        ]
        
        phone_instruction = ""
        if phone and phone in user_country_codes:
            phone_info = user_country_codes[phone]
            
            products_list = "\n".join([f"- {gem}" for gem in PRODUCT_PRICES.keys()])
            
            phone_instruction = f"""

CRITICAL CUSTOMER INFORMATION:
Customer Phone: {phone_info.get('formatted_phone', phone_info.get('phone_number', phone))}
Customer Country: {phone_info.get('country', 'Unknown')}
Customer Currency: {currency_code} ({currency_name})
Customer Timezone: {customer_timezone}

⚠️ IMPORTANT: All the above information is ALREADY KNOWN by the system.
- DO NOT ask customer for phone number - we have it
- DO NOT ask which country they're from - we know it
- These fields will be AUTO-POPULATED in your JSON output
- When generating JSON, leave "Customer Phone" as shown in template - system fills it automatically

{time_context}

📋 AVAILABLE PRODUCTS WITH PRICING:
{products_list}

💰 PRODUCT PRICING INSTRUCTIONS - READ CAREFULLY:
1. When customer asks about gemstone prices, ALWAYS provide pricing in their currency ({currency_code})
2. You have access to price ranges for all major gemstones
3. Format pricing clearly: "{currency_code} X - Y per carat"
4. If customer asks about a specific gemstone (e.g., "ruby price", "how much is blue sapphire"), provide:
   - Price range in THEIR currency
   - Brief note about factors affecting price (origin, treatment, quality)
   - Ask if they want details about a specific weight/quality

PRICING RESPONSE FORMAT:
"Our [GEMSTONE] prices range from {currency_code} [MIN] to [MAX] per carat. Prices vary based on origin, treatment, and quality. What weight/carat are you interested in?"

⚠ PRICING INSTRUCTIONS - READ CAREFULLY:
1. ALWAYS mention prices in {currency_code} when talking to this customer
2. When you see prices in INR or other currencies, convert them to {currency_code}
3. Use approximate conversions (you can estimate based on common rates)
4. Format: "approximately {currency_code} X" or "around {currency_code} X"

CALL FOR PRICE HANDLING:
When a product shows "Call for Price" or scraped data indicates "is_call_for_price":
- This means it's a PREMIUM, HIGH-VALUE gemstone (usually above USD 30,000)
- GENTLY suggest: "This is an exclusive high-value piece. I'd recommend connecting with our gemstone expert who can discuss the details and provide personalized assistance."
- DO NOT pressure, just nudge toward expert consultation
- Example: "This appears to be a premium gemstone. For pieces in this range, our experts can provide detailed information and the best pricing. Would you like me to connect you?"

📞 BUDGET ESCALATION JSON FORMAT:
When customer agrees to executive callback for budget discussion:

{{
  "Unique Ticket ID": "GP-[DDMMMYYYY]-[RANDOM6]",
  "Qualification Decision": "Budget Escalation - Call Requested",
  "Customer Phone": "{phone}",
  "Customer Name": "<collected name>",
  "Customer Email": "<collected email>",
  "User Phone Country": "{phone_info.get('country', 'Unknown')}",
  "User Currency": "{currency_code}",
  "User Timezone": "{customer_timezone}",
  "Customer Local Time": "{hours_status['customer_local_time']}",
  "Preferred Callback Date": "<customer's preferred date>",
  "Preferred Callback Time": "<customer's preferred time>",
  "Budget Mentioned": "<customer's stated budget>",
  "Product Interest": "<gemstone type and weight they were interested in>",
  "Conversation Summary": "<brief summary of what was discussed and why budget escalation needed>"
}}

IMPORTANT: After generating this JSON:
- DO NOT show ticket number to customer
- Confirm callback: "Thank you! Our executive will call you on [date/time]."
- If they ask for immediate contact: Provide appropriate sales desk number based on location

⚠ DISQUALIFICATION DETECTION:
When user shows clear signs of NOT being interested, you MUST generate a JSON with "Qualification Decision": "Disqualified"

DISQUALIFICATION TRIGGERS (any of these = instant disqualify):
❌ "not interested" / "no interest" / "not interested now"
❌ "goodbye" / "bye" / "later" / "maybe later"
❌ "it's a bot" / "you're a bot" / "not a human" / "talking to bot"
❌ "stop" / "leave me alone" / "don't contact"
❌ "just browsing" / "just looking" / "window shopping"
❌ Repeated "no" without engagement (3+ times)
❌ User says "no" after you offer to help/show options
❌ Hostile/rude responses like "f*ck off", "spam", etc.


WHEN DISQUALIFYING - CRITICAL RULES:
1. Respond politely: "Ok, I will pause here. If you ever want assistance, feel free to reach out. Have a great day!"
2. IMMEDIATELY generate JSON in the SAME response (not separately!)
3. JSON format:

{{
  \"Unique Ticket ID\": \"GP-[DDMMMYYYY]-[RANDOM6]\",
  \"Qualification Decision\": \"Disqualified\",
  \"Disqualification Reason\": \"<brief reason like 'User not interested' or 'User ended conversation' or 'No engagement after offer'>\",
  \"Customer Phone\": \"{phone}\",
  \"User Phone Country\": \"{phone_info.get('country', 'Unknown')}\",
  \"User Currency\": \"{currency_code}\",
  \"User Timezone\": \"{customer_timezone}\",
  \"Customer Local Time\": \"{hours_status['customer_local_time']}\",
  \"Message Sent During Business Hours\": \"{'Yes' if hours_status['is_within_business_hours'] else 'No'}\",
  \"Conversation Summary\": \"<1-2 sentence summary of what was discussed>\"
}}

4. The JSON MUST be in the same response as your polite message
5. This marks the conversation as ENDED internally and stops all future pings

EXAMPLE CORRECT DISQUALIFICATION:
User: "no"
Bot: "Ok, If you ever want assistance with gemstones, feel free to reach out. Have a great day!

{{
  \"Unique Ticket ID\": \"GP-05NOV2025-XK9P42\",
  \"Qualification Decision\": \"Disqualified\",
  \"Disqualification Reason\": \"User declined offer and not interested\",
  \"Customer Phone\": \"+91-9311466064\",
  \"User Phone Country\": \"India\",
  \"User Currency\": \"INR\",
  \"User Timezone\": \"Asia/Kolkata\",
  \"Customer Local Time\": \"02:30 PM\",
  \"Message Sent During Business Hours\": \"Yes\",
  \"Conversation Summary\": \"User asked about Ceylon Yellow Sapphire pricing in INR/USD/EUR but declined when offered product options\"
}}"

WRONG EXAMPLE (MISSING JSON):
User: "no"
Bot: "Ok, If you ever want help, feel free to reach out!" ❌ NO JSON GENERATED

REMEMBER: If you say "I will pause here" or similar ending phrases, you MUST include the disqualification JSON!
"""
        
        enhanced_system = SYSTEM_PROMPT + phone_instruction + """

⚠ CRITICAL CONVERSATION MEMORY RULES - READ CAREFULLY ⚠

Before EVERY response, you MUST check the conversation history for these key facts:
1. Purpose: Did they say "Astrological" or "Jewelry"? NEVER ask again if answered!
2. Gemstone: Did they mention a specific gemstone? NEVER ask again if answered!
3. Astrologer consultation: Did they say they consulted or haven't consulted? Remember this!
4. Budget/Weight: If mentioned, never ask again!

FORBIDDEN REPETITIONS:
❌ If user said "Astrological purpose" → DO NOT ask "astrological or jewelry?" again
❌ If user said "Haven't consulted astrologer" → DO NOT ask "did you consult?" again  
❌ If user mentioned "Ruby" → DO NOT ask "which gemstone?" again
❌ If user gave budget → DO NOT ask for budget again
❌ If you already described product details → DO NOT repeat them again
❌ NEVER ask for phone number - system already has it

⚠️ CRITICAL QUALIFICATION FLOW - READ CAREFULLY ⚠️

WHEN USER SENDS PRODUCT URL + SHOWS INTEREST:
After user says "yes"/"proceed"/"I want this" to a product:

STEP 1: Ask PURPOSE (astrological or jewelry?) ← DO THIS FIRST!
STEP 2: Ask for NAME
STEP 3: Ask for EMAIL
STEP 5: Generate JSON (gemstone, carat, budget already from product URL)

DO NOT:
❌ Ask for name/email BEFORE asking purpose
❌ Ask "what carat weight?" - it's in the product URL
❌ Ask "which gemstone?" - it's in the product URL
❌ Ask "what's your budget?" - they saw the price

EXAMPLE CORRECT FLOW:
User: [sends product URL]
You: "I can see you're viewing 6.56 carat Cat's Eye..."
User: "yes, I want this"
You: "Great! Is this for astrological purposes or jewelry?" ← FIRST
User: "astrological"
You: "Perfect! Could you share your name and email?" ← SECOND
User: "Sinku, sinku@gmail.com"
You: [Generate JSON - you know: Cat's Eye, 6.56 carats, price, purpose, name, email ]

🚫 CRITICAL: NEVER ASK FOR PHONE NUMBER
The system already knows the customer's phone number. When generating JSON:
- "Customer Phone" will be auto-filled by the system
- DO NOT ask customer for their phone number
- DO NOT include phone number collection in your conversation flow
- Focus on: Name, Email, Location (city/state), Gemstone interest, Budget

CRITICAL: AVOID REPEATING PRODUCT INFORMATION
If you already described a product in your previous message (price, carat, origin, etc.), DO NOT describe it again.
Just acknowledge their response and move to the NEXT step in qualification.

Example:
❌ WRONG: "I can see you're interested in Black Opal 0.2 carat. Price: INR 3,700 per carat..." (already said this before!)
✅ CORRECT: "Thank you Sinku! Got your email. To proceed, I'll need your phone number and location."

CORRECT BEHAVIOR:
✅ Build naturally on what they already told you
✅ Reference their answers: "Got it, so for astrological ruby..."
✅ Move forward in the qualification: purpose → gemstone → weight → budget → name/email/location
✅ Each question should be NEW information, never repeated
✅ NEVER repeat information you already provided in previous messages

CONVERSATION FLOW (ALWAYS follow this order):
1. **Purpose FIRST** (astrological/jewelry) - Ask this IMMEDIATELY after user shows interest
2. If astrological: consulted astrologer? which gemstone? (skip if product URL already provided)
3. Weight/carat range (skip if product URL already provided - you already know it!)
4. Budget range (skip if product URL already provided - they saw the price!)
5. Name, email
→ Once you have enough info, generate JSON and qualify

PRODUCT URL SPECIAL FLOW:
When user sends product URL + shows interest:
1. Purpose (astrological/jewelry) ← Ask FIRST
2. Name
3. Email
→ Generate JSON (gemstone, carat, budget already known from product)

KEEP CONVERSATION MOVING FORWARD:
- If you described a product → ask purpose
- If purpose given → ask for name and email
- NEVER circle back to information already discussed
- NEVER ask for info that was in the product URL they sent

PRODUCT URL HANDLING - CRITICAL INSTRUCTIONS:
When you receive product details from a URL scrape (user sent a product link):
⚠ THIS IS THE MOST IMPORTANT PART - READ CAREFULLY ⚠

The customer is viewing a SPECIFIC product with ALL details already known:
- Gemstone type: ALREADY KNOWN (e.g., "Blue Sapphire")
- Weight/Carat: ALREADY KNOWN (e.g., "3.5 carats")
- Price: ALREADY KNOWN (e.g., "INR 125,000")
- Origin, treatment, shape: ALREADY KNOWN

⚠ CRITICAL: CHECK IF PRICE IS "PER CARAT" OR "TOTAL" ⚠
- If scraped data shows "is_per_carat_price": TRUE → Price shown is PER CARAT
- You MUST calculate and mention BOTH per-carat AND total price
- Example: "The price is INR 40,000 per carat, so for 1.5 carat the total is INR 60,000"

YOUR RESPONSE MUST BE:
1. Acknowledge: "I can see you're viewing [Full Product Name] - [X] carat [Gemstone]"
2. Highlight 1-2 KEY features ONLY: "[Origin] origin, [Treatment] treatment" OR "[Color], [Shape] cut"
3. Quote price CORRECTLY:
   - If per-carat pricing: "Price: [CURRENCY] [X] per carat, total [CURRENCY] [Y] for [Z] carat"
   - If total pricing: "Total Price: approximately [CURRENCY] [CONVERTED_AMOUNT]"
4. Ask ONLY ONE question: "Would you like to proceed with this gemstone, or see similar options?"

AFTER USER CONFIRMS INTEREST (says "yes", "proceed", "I want this"):
⚠️ CRITICAL NEXT STEP: Ask about PURPOSE FIRST
- "Great! Is this for astrological purposes or jewelry?"
- DO NOT ask for name/email yet
- PURPOSE comes FIRST

THEN collect: Name → Email

⚠️ REMEMBER PRODUCT DETAILS:
Once user sends a product URL, you KNOW:
- Gemstone type (e.g., "Cat's Eye")
- Exact carat weight (e.g., "6.56 carats")
- Price
- Origin, treatment, shape

DO NOT ASK AGAIN FOR:
❌ "Which gemstone are you interested in?" - YOU ALREADY KNOW
❌ "What carat weight do you need?" - IT'S ALREADY SPECIFIED IN THE PRODUCT
❌ "What's your budget?" - THEY SAW THE PRICE

ONLY ask for information you DON'T have:
✅ Purpose (astrological/jewelry) - if not mentioned
✅ Name - if not provided
✅ Email - if not provided  

FORBIDDEN QUESTIONS FOR PRODUCT URLs:
❌ NEVER ask "Which gemstone are you interested in?" - ALREADY KNOWN
❌ NEVER ask "What carat weight do you need?" - ALREADY SPECIFIED  
❌ NEVER ask "What's your budget?" - THEY SAW THE PRICE
❌ NEVER ask "What origin do you prefer?" - ALREADY MENTIONED
❌ DO NOT repeat product details verbatim - summarize briefly

⚠️ CRITICAL PRODUCT URL MEMORY:
When user sends a product URL (e.g., gempundit.com/products/cats-eye-6.56-carats):
- The gemstone type is KNOWN (Cat's Eye)
- The carat weight is KNOWN (6.56 carats)
- The price is KNOWN (they saw it)
- Origin, treatment, shape are KNOWN

YOU ONLY NEED TO ASK:
1. Purpose (astrological/jewelry) ← FIRST
2. Name
3. Email

DO NOT ask about gemstone, carat, or budget - you already have this information!

CORRECT EXAMPLE (Per Carat Pricing):
User sends: https://gempundit.com/products/emerald-colombian-premium-plus (shows Rs.40,000 per carat, 1.5 carat)
Bot: "I can see you're viewing a 1.5 carat Colombian Emerald (Premium Plus quality). The price is Rs.40,000 per carat, so the total for this 1.5 carat stone is Rs.60,000 (approximately USD 720). Would you like to proceed with this gemstone, or see similar options?"

User: "yes" or "proceed" or "I want this"
Bot: "Great! Is this for astrological purposes or jewelry?"

User: "astrological"
Bot: "Perfect! Could you share your name and email address?"

User: "Rajesh, rajesh@example.com "
Bot: [Generate JSON with all details - gemstone, carat, price already known from URL]

CORRECT EXAMPLE (Total Pricing):
User sends: https://gempundit.com/products/blue-sapphire-3-5-carat-gp12345
Bot: "I can see you're viewing a 3.5 carat Blue Sapphire (Ceylon origin, unheated). Total Price: approximately USD 1,500. Would you like to proceed with this gemstone, or see similar options?"

User: "yes"
Bot: "Great! Is this for astrological purposes or jewelry?"

WRONG EXAMPLE (DON'T DO THIS):
User: "yes" (after seeing product)
Bot: "Great! Could you share your name and email?" ❌ (Should ask PURPOSE first!)

User: "Rajesh, rajesh@example.com"
Bot: "What carat weight are you looking for?" ❌ (Already in the product URL!)

Bot: "Which gemstone are you interested in?" ❌ (Already in the product URL!)

PROCEED TO QUALIFICATION:
After confirming interest in the product:
- Ask for: Name, Email (if not already collected)
- Generate JSON with product details pre-filled
- Mark as qualified lead

⚠ CRITICAL: DESCRIBE PRODUCT ONLY ONCE
The above product description format should ONLY be used when:
- User FIRST sends the product URL
- This is the FIRST time discussing this specific product

If you already described this product in a previous message:
❌ DO NOT repeat "I can see you're viewing..."
❌ DO NOT repeat price, carat, origin, treatment details
✅ Just acknowledge their response and continue qualification: "Thank you! To proceed, could you share your location?"

🛒 CHECKOUT CART URL HANDLING - CRITICAL:
When user sends URL like "https://www.gempundit.com/checkout/cart/":
⚠ This is a PRIVATE cart page - you CANNOT access it

YOUR RESPONSE MUST BE:
"I can see you've shared your cart link! However, for security reasons, I'm unable to access your cart directly.

Could you please help me by:
1. Click on the product image in your cart
2. Copy that specific product URL
3. Send it to me

This way I can see exactly what you're interested in and assist you better."

DO NOT:
❌ Try to scrape the cart URL
❌ Say "I cannot access" without explaining why
❌ Make customer feel like they did something wrong

ALTERNATIVE: If they describe what's in cart instead of sending URL:
- Ask them to describe: gemstone type, weight, any specifications they remember
- Help them find the product based on description

CATEGORY URL HANDLING:
When you receive category page info:
- Note the gemstone type they're browsing
- Ask about their specific requirements (weight, budget in THEIR CURRENCY)
- Don't ask which gemstone if it's clear from the category

IMAGE ANALYSIS HANDLING:
When you receive image analysis (user sent gemstone/jewelry photo):

For *Product Screenshots* (from any online store):
- **NEVER mention** "competitor", "another store", or any external website
- Acknowledge: "I can see you're interested in this [X carat] [gemstone]! Let me help you find it."
- Extract key details: gemstone type, weight, price if shown
- Say: "Would you like me to show you similar certified options at GemPundit?"
- Use extracted specs to qualify them faster

For *Gemstone in Ring/Jewelry*:
- Compliment if it looks good: "That's a beautiful piece!"
- Ask: "Are you looking for something similar, or is this a reference for what you want?"
- Note gemstone type, setting style, metal for future reference
- Don't ask "which gemstone" if already clear from image

For *Loose Gemstone/Palm/Raw Stone*:
- Acknowledge what you see: "I can see a [color] [gemstone type]"
- Ask purpose: "Are you looking to buy something similar for astrological use or jewelry?"
- If they want valuation: "For accurate pricing, I'd need carat weight and certification. Would you like help finding certified stones?"

For *Certificate Images*:
- Read and acknowledge: "I can see the [Lab Name] certificate for a [weight] [gemstone]"
- Ask: "Are you looking to verify this, or buy something similar?"
- If buying: proceed with qualification based on cert specs

GENERAL IMAGE RULES:
✅ Always extract gemstone type from image - don't ask "which gemstone?" again
✅ Use image details to speed up qualification
✅ Be helpful and professional with all product inquiries
✅ If image quality is poor, politely ask for better photo or more details


GENERAL GEMSTONE QUESTIONS:
When user asks general gemstone questions (benefits, how to wear, which finger, etc.):
- Answer in ONE LINE (maximum 25 words) using your knowledge
- Be concise and helpful
- Then ask one short follow-up question to continue qualification

Example:
User: "What are the benefits of wearing ruby?"
You: "Ruby boosts confidence, vitality, and leadership qualities. It's also beneficial for career and relationships. Are you looking for astrological or jewelry purposes?"

DO NOT include URLs or citations. Just answer briefly and move the conversation forward.

TICKET ID FORMAT:
When generating JSON for qualified leads, use this format for Unique Ticket ID:
GP-[DDMMMYYYY]-[RANDOM6]
Where:
- DDMMMYYYY = Date in format like 03NOV2025
- RANDOM6 = 6 random uppercase alphanumeric characters
Example: GP-03NOV2025-A7K9P2


NEVER:
❌ Repeat questions already answered
❌ Use multiple URLs or markdown links
❌ Ask "which gemstone" if they sent a product/category URL
❌ Break the natural conversation flow
❌ Use uuid format for Ticket ID
❌ Quote prices in wrong currency (always use customer's currency)
❌ Confuse per-carat price with total price
❌ Forget to calculate total price when per-carat pricing is detected
❌ Ignore timezone/business hours information when qualifying leads"""
        
        messages[0] = {"role": "system", "content": enhanced_system}
        
        resp = client.responses.create(
            model=OPENAI_MODEL,
            input=messages
        )
        
        output_text = ""
        
        try:
            if hasattr(resp, 'output') and resp.output:
                for block in resp.output:
                    if block is None:
                        continue
                    if hasattr(block, 'content') and block.content:
                        for item in block.content:
                            if hasattr(item, 'text') and item.text:
                                output_text += item.text
                    elif hasattr(block, 'text') and block.text:
                        output_text += block.text
                    elif isinstance(block, str):
                        output_text += block
        except Exception as parse_err:
            logger.warning(f"Response parsing failed: {parse_err}")
        
        if not output_text:
            try:
                resp_dict = resp.model_dump() if hasattr(resp, 'model_dump') else resp.dict()
                if 'output' in resp_dict:
                    for block in resp_dict['output']:
                        if isinstance(block, dict):
                            if 'content' in block:
                                for item in block['content']:
                                    if isinstance(item, dict) and 'text' in item:
                                        output_text += item['text']
                            elif 'text' in block:
                                output_text += block['text']
                        elif isinstance(block, str):
                            output_text += block
            except Exception as parse_err2:
                logger.warning(f"Fallback parsing failed: {parse_err2}")
        
        if not output_text:
            output_text = str(resp)
            logger.warning(f"Using raw response as fallback")
        
        output_text = output_text.strip() or "Sorry, I couldn't generate a reply."
        logger.info(f"💬 GPT output: {output_text[:120]}...")
        return {"output_text": output_text}

    except Exception as e:
        logger.error(f"call_openai_with_websearch() error: {e}\n{traceback.format_exc()}")
        return {"output_text": "I'm having trouble right now. Could you try again?"}


def call_openai(user_text: str, context: list, scraped_data: dict = None, phone: str = None):
    """Wrapper for OpenAI calls"""
    return call_openai_with_websearch(user_text, context, scraped_data, phone)


@app.route("/webhook", methods=["GET"])
@app.route("/webhook", methods=["POST"])
@app.route("/health", methods=["GET"])
@app.route("/chatbotmessage", methods=["POST"])

@app.route("/chatbotmessage", methods=["POST"])
def process_combined_message(phone, combined_text):
    """Process the combined/batched message"""
    try:
        # Track bot response time for ping system
        last_bot_response_time[phone] = time.time()
        
        logger.info(f"🔄 Processing combined message from {phone}: {combined_text[:100]}")
        
        # Get country info
        if phone not in user_country_codes:
            country_info = extract_country_code(phone)
            user_country_codes[phone] = country_info
        else:
            country_info = user_country_codes[phone]
        
        # Build context (Chakra handles history, so start fresh)
        context = []
        
        # Check for URLs and scrape
        urls, skus = extract_urls_and_skus(combined_text)
        scraped_data = None
        
        if urls:
            for url in urls:
                if is_gempundit_url(url):
                    scraped_data = scrape_url(url)
                    if scraped_data and not scraped_data.get("error"):
                        logger.info(f"📦 Scraped: {json.dumps(scraped_data, ensure_ascii=False)[:150]}")
                    break
        
        # Enhanced text with country info
        customer_timezone = country_info.get('timezone', 'UTC')
        enhanced_text = f"{combined_text}\n\n[Customer Info: {country_info['country']}, Currency: {country_info['currency_code']}, Timezone: {customer_timezone}]"
        
        # Call OpenAI
        result = call_openai(enhanced_text, context, scraped_data, phone)
        bot_reply = result["output_text"]
        
        # Extract JSON
        json_blocks, cleaned_reply = extract_json_blocks(bot_reply)
        
        if json_blocks:
            lead_json = json_blocks[0]
            qualification = lead_json.get("Qualification Decision", "").lower()
            
            if "qualified" in qualification and "disqualified" not in qualification:
                route = "sales"
            elif "disqualified" in qualification:
                route = "disqualified"
            else:
                route = "lq"
            
            logger.info(f"✅ LEAD GENERATED - {qualification} → {route}")
            log_lead(phone, lead_json)
            
            return {
                "response": {
                    "message": cleaned_reply,
                    "route_to": route,
                    "qualification_status": qualification,
                    "confidence_score": lead_json.get("Conversion Probability (%)", 0),
                    "lead_generated": True
                },
                "data": lead_json
            }
        
        logger.info("💬 Still qualifying")
        return {
            "response": {
                "message": bot_reply,
                "route_to": None,
                "qualification_status": "qualifying",
                "confidence_score": None,
                "lead_generated": False
            },
            "data": {},
            "followup": {
                "schedule": True,
                "delay_minutes": 3,  # First ping at 3 minutes
                "ping_number": 1,
                "message": "generate"  # Chakra should call /generate_ping endpoint
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Process error: {e}\n{traceback.format_exc()}")
        return {
            "error": str(e),
            "response": {
                "message": "I apologize, there was an error. Please try again.",
                "route_to": "lq",
                "qualification_status": "error",
                "confidence_score": 0,
                "lead_generated": False
            },
            "data": {}
        }


@app.route("/chatbotmessage", methods=["POST"])
def chatbot_message():
    """
    Chakra endpoint with message batching
    Combines messages sent within 10 seconds
    """
    try:
        data = request.get_json()
        logger.info(f"📨 Chakra: {json.dumps(data, ensure_ascii=False)[:200]}")
        
        phone = data.get("PhoneNumber", "").strip()
        text = data.get("CustomerMessage", "").strip()
        
        if not phone or not text:
            return jsonify({"error": "Missing PhoneNumber or CustomerMessage"}), 400
        
        now = time.time()
        
        # Initialize for new phone
        if phone not in pending_messages:
            pending_messages[phone] = []
            last_msg_time[phone] = 0
        
        time_since_last = now - last_msg_time[phone]
        
        # Cancel existing batch timer if any
        if phone in batch_timers:
            batch_timers[phone].cancel()
            logger.info(f"⏱️ Cancelled previous timer for {phone}")
        
        # Add current message to batch
        pending_messages[phone].append(text)

        
        # Track user message time (for ping system)
        user_last_message_time[phone] = now
        ping_count[phone] = 0  # Reset ping count when user responds        last_msg_time[phone] = now
        
        # If within combine window and not first message, just accumulate
        if time_since_last < COMBINE_WINDOW and len(pending_messages[phone]) > 1:
            logger.info(f"📦 Batching message #{len(pending_messages[phone])} from {phone}: {text[:50]}")
            
            # Set timer to process after COMBINE_WINDOW
            def process_batch():
                if phone in pending_messages and pending_messages[phone]:
                    combined = " ".join(pending_messages[phone])
                    pending_messages[phone] = []
                    batch_timers.pop(phone, None)
                    logger.info(f"⏰ Timer fired - batch ready: {combined[:100]}")
            
            timer = threading.Timer(COMBINE_WINDOW, process_batch)
            timer.start()
            batch_timers[phone] = timer
            
            # Return minimal acknowledgment
            return jsonify({
                "response": {
                    "message": "",  # Empty - don't show to user
                    "route_to": None,
                    "qualification_status": "batching",
                    "confidence_score": None,
                    "lead_generated": False
                },
                "data": {"batching": True, "batch_size": len(pending_messages[phone])}
            }), 200
        
        # Time to process (either first message or gap > 10 seconds)
        combined_text = " ".join(pending_messages[phone])
        pending_messages[phone] = []  # Clear batch
        batch_timers.pop(phone, None)
        
        logger.info(f"✅ Processing combined: {combined_text[:150]}")
        
        # Process the combined message
        result = process_combined_message(phone, combined_text)
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"❌ Chakra error: {e}\n{traceback.format_exc()}")
        return jsonify({
            "error": str(e),
            "response": {
                "message": "I apologize, there was an error. Please try again.",
                "route_to": "lq",
                "qualification_status": "error",
                "confidence_score": 0,
                "lead_generated": False
            },
            "data": {}
        }), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.datetime.utcnow().isoformat()}), 200

if __name__ == "__main__":
    if not OPENAI_API_KEY:
        logger.error("❌ OPENAI_API_KEY not set")
        exit(1)
    
    logger.info("=" * 60)
    logger.info("🚀 GEMPUNDIT CHAKRA BOT - COMPLETE VERSION")
    logger.info("=" * 60)
    logger.info(f"📍 Port: {PORT}")
    logger.info(f"🤖 Model: {OPENAI_MODEL}")
    logger.info(f"🔗 POST /chatbotmessage (Chakra)")
    logger.info(f"💚 GET /health")
    logger.info("=" * 60)
    
    app.run(host="0.0.0.0", port=PORT, debug=False)

@app.route("/generate_ping", methods=["POST"])
def generate_ping():
    """
    Generate personalized follow-up message for Chakra
    Called when it's time to send a ping
    """
    try:
        data = request.get_json()
        phone = data.get("PhoneNumber", "").strip()
        ping_number = data.get("ping_number", 1)  # 1, 2, or 3
        conversation_context = data.get("conversation_context", "")  # Last few messages
        
        if not phone:
            return jsonify({"error": "Missing PhoneNumber"}), 400
        
        # Get country info
        if phone not in user_country_codes:
            country_info = extract_country_code(phone)
            user_country_codes[phone] = country_info
        else:
            country_info = user_country_codes[phone]
        
        # Generate personalized ping based on conversation context
        ping_prompt = f"""Based on this conversation context, generate a friendly, natural follow-up message to re-engage the customer.

This is ping #{ping_number} in the sequence (1=gentle, 2=more direct, 3=last attempt).

Conversation context:
{conversation_context}

Customer info: {country_info['country']}, Currency: {country_info['currency_code']}

Rules:
- Keep it short (1-2 sentences)
- Sound natural, not robotic
- Reference what they were discussing if relevant
- For ping 1: Gentle check-in
- For ping 2: More direct, offer help
- For ping 3: Final attempt, offer callback or alternative

Generate ONLY the message text, no JSON, no formatting."""
        
        messages = [
            {"role": "system", "content": "You are a friendly gemstone advisor following up with a customer."},
            {"role": "user", "content": ping_prompt}
        ]
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=150,
            temperature=0.8
        )
        
        ping_message = response.choices[0].message.content.strip()
        
        logger.info(f"📌 Generated ping #{ping_number} for {phone}: {ping_message[:50]}")
        
        # Calculate next ping delay
        next_ping_number = ping_number + 1
        if next_ping_number <= len(PING_SCHEDULE):
            next_delay = PING_SCHEDULE[next_ping_number - 1] / 60  # Convert to minutes
            schedule_next = True
        else:
            next_delay = None
            schedule_next = False
        
        return jsonify({
            "message": ping_message,
            "ping_number": ping_number,
            "followup": {
                "schedule": schedule_next,
                "delay_minutes": next_delay,
                "ping_number": next_ping_number
            }
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Ping generation error: {e}\n{traceback.format_exc()}")

  #end      
        return jsonify({"error": str(e)}), 500
