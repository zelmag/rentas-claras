"""
RentasClaras: Vision OCR for Withdrawal Code Extraction
========================================================

Uses LLM Vision (GPT-4V, Claude Vision) to extract "Retiro sin Tarjeta" 
(cardless withdrawal) codes from tenant screenshots.

Supported Banks:
- BBVA (Bancomer)
- Banorte
- Santander
- HSBC
- Citibanamex
- Scotiabank

Extracted Fields:
- Bank Name
- Withdrawal Code (10-12 digits)
- Amount (MXN)
- Expiration (if visible)

Author: RentasClaras Engineering
Date: December 2024
"""

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pathlib import Path


class MexicanBank(Enum):
    """Mexican banks that support Retiro sin Tarjeta."""
    BBVA = "BBVA"
    BANORTE = "Banorte"
    SANTANDER = "Santander"
    HSBC = "HSBC"
    CITIBANAMEX = "Citibanamex"
    SCOTIABANK = "Scotiabank"
    BANCO_AZTECA = "Banco Azteca"
    UNKNOWN = "Desconocido"


@dataclass
class WithdrawalCodeExtraction:
    """Result of OCR extraction from a withdrawal screenshot."""
    success: bool
    bank: MexicanBank
    code: Optional[str]
    amount: Optional[Decimal]
    expiration: Optional[str]
    raw_text: Optional[str]
    confidence: float  # 0.0 to 1.0
    error_message: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if extraction has minimum required fields."""
        return (
            self.success
            and self.code is not None
            and len(self.code) >= 6
            and self.amount is not None
            and self.amount > Decimal("0")
        )


# =============================================================================
# LLM VISION PROMPT
# =============================================================================

EXTRACTION_PROMPT = """Analiza esta imagen de un "Retiro sin Tarjeta" (retiro de efectivo sin tarjeta) de un banco mexicano.

Extrae la siguiente información en formato JSON:

{
  "bank": "nombre del banco (BBVA, Banorte, Santander, HSBC, Citibanamex, Scotiabank, etc.)",
  "code": "código de retiro (10-12 dígitos, puede tener espacios o guiones)",
  "amount": "monto en pesos mexicanos (solo el número, sin $ ni comas)",
  "expiration": "fecha/hora de vencimiento si es visible (formato: YYYY-MM-DD HH:MM)",
  "raw_text": "texto relevante encontrado en la imagen"
}

REGLAS IMPORTANTES:
1. El código de retiro típicamente tiene 10-12 dígitos
2. El monto debe extraerse SIN el símbolo $ y SIN comas (ej: "3200.00")
3. Si no puedes identificar algún campo, usa null
4. Si la imagen NO es de un retiro sin tarjeta, responde con:
   {"error": "La imagen no parece ser un comprobante de retiro sin tarjeta"}

Responde ÚNICAMENTE con el JSON, sin texto adicional."""


# =============================================================================
# EXTRACTION LOGIC
# =============================================================================

def extract_withdrawal_code(
    image_data: bytes,
    provider: str = "openai"  # "openai", "anthropic", "local"
) -> WithdrawalCodeExtraction:
    """
    Extract withdrawal code information from a screenshot.
    
    Args:
        image_data: Raw bytes of the image (JPEG/PNG)
        provider: LLM provider to use ("openai", "anthropic", "local")
    
    Returns:
        WithdrawalCodeExtraction with extracted data
    """
    # Encode image for API
    base64_image = base64.b64encode(image_data).decode("utf-8")
    
    # Detect image type
    if image_data[:8] == b'\x89PNG\r\n\x1a\n':
        media_type = "image/png"
    else:
        media_type = "image/jpeg"
    
    # Call appropriate provider
    if provider == "openai":
        return _extract_with_openai(base64_image, media_type)
    elif provider == "anthropic":
        return _extract_with_anthropic(base64_image, media_type)
    else:
        return _extract_with_regex(image_data)


def _extract_with_openai(base64_image: str, media_type: str) -> WithdrawalCodeExtraction:
    """
    Extract using OpenAI GPT-4 Vision.
    
    In production:
    ```python
    from openai import OpenAI
    
    client = OpenAI()
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=500
    )
    
    json_response = response.choices[0].message.content
    return _parse_extraction_response(json_response)
    ```
    """
    print("🔍 [SPIKE] Would call OpenAI GPT-4V for extraction")
    
    # Return simulated successful extraction
    return WithdrawalCodeExtraction(
        success=True,
        bank=MexicanBank.BBVA,
        code="847293102934",
        amount=Decimal("4850.00"),
        expiration="2025-01-05 20:00",
        raw_text="Retiro sin Tarjeta BBVA - Código: 847293102934 - Monto: $4,850.00",
        confidence=0.95
    )


def _extract_with_anthropic(base64_image: str, media_type: str) -> WithdrawalCodeExtraction:
    """
    Extract using Anthropic Claude Vision.
    
    In production:
    ```python
    import anthropic
    
    client = anthropic.Anthropic()
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image
                        }
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT
                    }
                ]
            }
        ]
    )
    
    json_response = response.content[0].text
    return _parse_extraction_response(json_response)
    ```
    """
    print("🔍 [SPIKE] Would call Anthropic Claude Vision for extraction")
    
    return WithdrawalCodeExtraction(
        success=True,
        bank=MexicanBank.BANORTE,
        code="938571029384",
        amount=Decimal("3200.00"),
        expiration="2025-01-05 18:00",
        raw_text="Banorte - Retiro sin Tarjeta - 938571029384 - $3,200.00",
        confidence=0.92
    )


def _extract_with_regex(image_data: bytes) -> WithdrawalCodeExtraction:
    """
    Fallback extraction using regex patterns (for OCR'd text).
    
    This would be used if you first run local OCR (Tesseract, etc.)
    and then parse the resulting text.
    """
    print("🔍 [SPIKE] Would run local OCR + regex extraction")
    
    return WithdrawalCodeExtraction(
        success=False,
        bank=MexicanBank.UNKNOWN,
        code=None,
        amount=None,
        expiration=None,
        raw_text=None,
        confidence=0.0,
        error_message="Local OCR not implemented in spike"
    )


def _parse_extraction_response(json_string: str) -> WithdrawalCodeExtraction:
    """Parse the LLM's JSON response into a structured result."""
    try:
        # Clean up response (remove markdown code blocks if present)
        json_string = json_string.strip()
        if json_string.startswith("```"):
            json_string = re.sub(r"```json?\s*", "", json_string)
            json_string = json_string.rstrip("`")
        
        data = json.loads(json_string)
        
        # Check for error
        if "error" in data:
            return WithdrawalCodeExtraction(
                success=False,
                bank=MexicanBank.UNKNOWN,
                code=None,
                amount=None,
                expiration=None,
                raw_text=None,
                confidence=0.0,
                error_message=data["error"]
            )
        
        # Parse bank
        bank_name = data.get("bank", "").upper()
        bank = MexicanBank.UNKNOWN
        for b in MexicanBank:
            if b.value.upper() in bank_name or bank_name in b.value.upper():
                bank = b
                break
        
        # Parse code (remove spaces/dashes)
        code = data.get("code")
        if code:
            code = re.sub(r"[\s\-]", "", str(code))
        
        # Parse amount
        amount = None
        if data.get("amount"):
            try:
                amount_str = re.sub(r"[,$]", "", str(data["amount"]))
                amount = Decimal(amount_str)
            except:
                pass
        
        return WithdrawalCodeExtraction(
            success=True,
            bank=bank,
            code=code,
            amount=amount,
            expiration=data.get("expiration"),
            raw_text=data.get("raw_text"),
            confidence=0.85
        )
        
    except json.JSONDecodeError as e:
        return WithdrawalCodeExtraction(
            success=False,
            bank=MexicanBank.UNKNOWN,
            code=None,
            amount=None,
            expiration=None,
            raw_text=json_string,
            confidence=0.0,
            error_message=f"Failed to parse JSON: {str(e)}"
        )


# =============================================================================
# VALIDATION & FORMATTING
# =============================================================================

def validate_withdrawal_code(code: str) -> bool:
    """
    Validate a Mexican withdrawal code format.
    
    Most banks use 10-12 digit numeric codes.
    """
    if not code:
        return False
    
    # Remove any formatting
    clean_code = re.sub(r"[\s\-]", "", code)
    
    # Check length and numeric
    return clean_code.isdigit() and 6 <= len(clean_code) <= 14


def format_code_for_display(code: str) -> str:
    """Format code with spaces for readability (groups of 4)."""
    clean_code = re.sub(r"[\s\-]", "", code)
    return " ".join([clean_code[i:i+4] for i in range(0, len(clean_code), 4)])


# =============================================================================
# MESSAGE GENERATION
# =============================================================================

def generate_code_confirmation_message(extraction: WithdrawalCodeExtraction) -> str:
    """
    Generate a confirmation message for the tenant after extracting their code.
    
    Uses formal "usted" tone.
    """
    if not extraction.is_valid():
        return """❌ No pudimos procesar la imagen.

Por favor, envíe una captura de pantalla clara del código de retiro que muestre:
• El código completo
• El monto
• El banco

Asegúrese de que la imagen esté bien iluminada y el texto sea legible."""
    
    formatted_code = format_code_for_display(extraction.code)
    
    message = f"""✓ *Código de retiro registrado*

🏦 Banco: {extraction.bank.value}
🔢 Código: `{formatted_code}`
💰 Monto: ${extraction.amount:,.2f} MXN"""
    
    if extraction.expiration:
        message += f"\n⏰ Vence: {extraction.expiration}"
    
    message += """

Le confirmaremos una vez que el retiro sea realizado.

Gracias."""
    
    return message


def generate_landlord_alert(
    extraction: WithdrawalCodeExtraction,
    tenant_name: str,
    unit: str
) -> str:
    """Generate an alert message for the landlord."""
    if not extraction.is_valid():
        return f"⚠️ {tenant_name} ({unit}) envió una imagen pero no pude extraer el código."
    
    formatted_code = format_code_for_display(extraction.code)
    
    message = f"""🏧 *Nuevo código de retiro*

👤 Inquilino: {tenant_name} ({unit})
🏦 Banco: {extraction.bank.value}
🔢 Código: `{formatted_code}`
💰 Monto: ${extraction.amount:,.2f} MXN"""
    
    if extraction.expiration:
        message += f"\n⏰ Vence: {extraction.expiration}"
    
    message += f"""

Responde "Retiré {extraction.code[:6]}" cuando lo cobres."""
    
    return message


# =============================================================================
# DEMO
# =============================================================================

def run_vision_demo():
    """Demonstrate the Vision OCR extraction."""
    print("=" * 70)
    print("🏠 RENTASCLARAS - Vision OCR Demo")
    print("=" * 70)
    print()
    
    print("📸 EXTRACTION PROMPT:")
    print("-" * 50)
    print(EXTRACTION_PROMPT)
    print()
    
    # Simulate extraction with OpenAI
    print("=" * 70)
    print("🔍 SIMULATED EXTRACTION (OpenAI GPT-4V)")
    print("=" * 70)
    print()
    
    # In production: would receive actual image bytes
    dummy_image = b"\x89PNG\r\n\x1a\n..."  # Placeholder
    
    result = extract_withdrawal_code(dummy_image, provider="openai")
    
    print(f"Success: {result.success}")
    print(f"Bank: {result.bank.value}")
    print(f"Code: {result.code}")
    print(f"Amount: ${result.amount:,.2f}" if result.amount else "Amount: N/A")
    print(f"Expiration: {result.expiration or 'N/A'}")
    print(f"Confidence: {result.confidence:.0%}")
    print(f"Valid: {result.is_valid()}")
    print()
    
    # Generate messages
    print("=" * 70)
    print("📱 GENERATED MESSAGES")
    print("=" * 70)
    print()
    
    print("--- TO TENANT ---")
    print(generate_code_confirmation_message(result))
    print()
    
    print("--- TO LANDLORD ---")
    print(generate_landlord_alert(result, "María González", "Ensenada 3"))
    print()
    
    # Test with Anthropic
    print("=" * 70)
    print("🔍 SIMULATED EXTRACTION (Anthropic Claude)")
    print("=" * 70)
    print()
    
    result_claude = extract_withdrawal_code(dummy_image, provider="anthropic")
    print(f"Bank: {result_claude.bank.value}")
    print(f"Code: {format_code_for_display(result_claude.code)}")
    print(f"Amount: ${result_claude.amount:,.2f}")
    print()
    
    # Validation tests
    print("=" * 70)
    print("✅ CODE VALIDATION TESTS")
    print("=" * 70)
    print()
    
    test_codes = [
        ("847293102934", True),
        ("8472 9310 2934", True),  # With spaces
        ("84729310", True),  # Shorter but valid
        ("12345", False),  # Too short
        ("ABC123", False),  # Contains letters
        ("", False),  # Empty
    ]
    
    for code, expected in test_codes:
        result = validate_withdrawal_code(code)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{code}' → valid={result} (expected={expected})")


if __name__ == "__main__":
    run_vision_demo()
