# utils.py
"""
Utility functions for VueloDigno application.
Contains helper functions for text formatting, date handling, and social media integration.
"""

import re
from datetime import datetime

# Airline Twitter handles for social pressure feature
AIRLINE_TWITTER_HANDLES = {
    'Volaris': '@viajaVolaris',
    'VivaAerobus': '@VivaTeEscucha',
    'Aeromexico': '@Aeromexico'
}

# Spanish month translations
MONTHS_SPANISH = {
    'January': 'enero', 'February': 'febrero', 'March': 'marzo',
    'April': 'abril', 'May': 'mayo', 'June': 'junio',
    'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
    'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
}


def generate_tweet_text(flight_data: dict, compensation_amount: float) -> str:
    """
    Generate pre-filled tweet for social pressure.

    Args:
        flight_data: Dictionary containing flight information
        compensation_amount: Calculated compensation amount in MXN

    Returns:
        Pre-formatted tweet text with airline handle and legal references
    """
    airline = flight_data['airline']
    airline_handle = AIRLINE_TWITTER_HANDLES.get(airline, f'@{airline}')

    # Format compensation amount
    comp_text = f"${compensation_amount:,.0f} MXN" if compensation_amount > 0 else "compensación"

    # Get delay hours text
    delay_hours = flight_data['delay_hours']
    if delay_hours == 1.5:
        delay_text = "1-2 horas"
    elif delay_hours == 3.0:
        delay_text = "2-4 horas"
    elif delay_hours == 5.0:
        delay_text = "más de 4 horas"
    else:
        delay_text = f"{delay_hours} horas"

    # Build tweet with compensation amount and legal citation
    tweet = f"""{airline_handle} me debe {comp_text} por retraso de {delay_text} en el vuelo {flight_data['flight_number']}.

Ya les mandé los datos por email. Plazo legal: 10 días (Art. 47 Bis, Ley de Aviación Civil).

Si no responden, presentaré queja con @Profeco

#DerechosDelPasajero #PROFECO"""

    return tweet


def convert_markdown_to_html(text: str) -> str:
    """
    Convert markdown formatting to HTML for the front-end preview.

    Args:
        text: Markdown-formatted text

    Returns:
        HTML-formatted text with <strong>, <li>, <ul>, and <br> tags
    """
    # Bold: **text**
    text = re.sub(r'\*\*([^\*]+?)\*\*', r'<strong>\1</strong>', text)

    # Bullet points: * item
    text = re.sub(r'^\*\s+(.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)

    # Wrap consecutive list items in <ul>
    text = re.sub(r'(<li>.+?</li>\n)+', lambda m: f'<ul>{m.group(0)}</ul>', text)

    # Line breaks
    text = text.replace('\n', '<br>\n')

    return text


def format_date_spanish(date_obj: datetime) -> str:
    """
    Format date in Spanish: DD de MONTH de YYYY

    Args:
        date_obj: Python datetime object

    Returns:
        Formatted date string in Spanish (e.g., "15 de enero de 2025")
    """
    # Try using locale first
    try:
        date_str = date_obj.strftime('%d de %B de %Y')
        # If month is in English, translate it
        for eng, esp in MONTHS_SPANISH.items():
            date_str = date_str.replace(eng, esp)
        return date_str
    except Exception:
        # Fallback to manual formatting
        day = date_obj.day
        month = MONTHS_SPANISH.get(date_obj.strftime('%B'), date_obj.strftime('%B'))
        year = date_obj.year
        return f"{day} de {month} de {year}"


def get_delay_text(delay_hours: float) -> str:
    """
    Convert delay hours to human-readable Spanish text.

    Args:
        delay_hours: Float representing delay duration

    Returns:
        Human-readable delay description in Spanish
    """
    if delay_hours == 1.5:
        return "1-2 horas"
    elif delay_hours == 3.0:
        return "2-4 horas"
    elif delay_hours == 5.0:
        return "más de 4 horas"
    else:
        return f"{delay_hours} horas"


def format_currency_mxn(amount: float) -> str:
    """
    Format amount as Mexican Pesos.

    Args:
        amount: Numeric amount

    Returns:
        Formatted currency string (e.g., "$2,500.00 MXN")
    """
    return f"${amount:,.2f} MXN"
