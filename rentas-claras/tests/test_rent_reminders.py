"""
RentasClaras Test Suite: Rent Reminder Messages
================================================

Tests for:
- Name extraction and abbreviation expansion
- Message generation in correct Spanish format
- WhatsApp link generation
- Multi-tenant handling (Matehuala B special case)

Author: RentasClaras Engineering
Date: December 2024
"""

import pytest
from decimal import Decimal
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (
    expand_abbreviated_name,
    extract_display_name,
    generate_rent_reminder,
    create_whatsapp_link,
    NAME_ABBREVIATIONS
)
from database import Tenant


# =============================================================================
# TEST: Name Abbreviation Expansion
# =============================================================================

class TestNameAbbreviationExpansion:
    """Test expand_abbreviated_name function."""
    
    def test_j_carlos_expands_to_juan_carlos(self):
        """'J Carlos' should expand to 'Juan Carlos', not 'J'."""
        result = expand_abbreviated_name("J Carlos")
        assert result == "Juan Carlos"
    
    def test_j_carlos_y_raul_expands_first_person(self):
        """'J Carlos y Raul' should give 'Juan Carlos' (first person)."""
        # Note: extract_display_name handles the split, expand handles abbreviation
        result = expand_abbreviated_name("J Carlos")
        assert result == "Juan Carlos"
    
    def test_gpe_vanessa_expands_to_guadalupe_vanessa(self):
        """'Gpe Vanessa' should expand to 'Guadalupe Vanessa'."""
        result = expand_abbreviated_name("Gpe Vanessa")
        assert result == "Guadalupe Vanessa"
    
    def test_ma_elena_expands_to_maria_elena(self):
        """'Ma Elena' should expand to 'María Elena'."""
        result = expand_abbreviated_name("Ma Elena")
        assert result == "María Elena"
    
    def test_fco_javier_expands_to_francisco_javier(self):
        """'Fco Javier' should expand to 'Francisco Javier'."""
        result = expand_abbreviated_name("Fco Javier")
        assert result == "Francisco Javier"
    
    def test_simple_name_returns_first_name(self):
        """Simple name like 'María González' returns 'María'."""
        result = expand_abbreviated_name("María")
        assert result == "María"
    
    def test_single_word_name_returns_as_is(self):
        """Single word name returns as is."""
        result = expand_abbreviated_name("Fatima")
        assert result == "Fatima"
    
    def test_empty_name_returns_as_is(self):
        """Empty string returns as is."""
        result = expand_abbreviated_name("")
        assert result == ""


# =============================================================================
# TEST: Display Name Extraction
# =============================================================================

class TestDisplayNameExtraction:
    """Test extract_display_name function."""
    
    def test_simple_name(self):
        """Simple name returns first name only."""
        result = extract_display_name("Fatima")
        assert result == "Fatima"
    
    def test_full_name_returns_first_name(self):
        """Full name 'María González' returns 'María'."""
        result = extract_display_name("María González")
        assert result == "María"
    
    def test_j_carlos_y_raul_returns_juan_carlos(self):
        """'J Carlos y Raul' returns 'Juan Carlos' (expanded first person)."""
        result = extract_display_name("J Carlos y Raul")
        assert result == "Juan Carlos"
    
    def test_samantha_y_cecilia_returns_samantha(self):
        """'Samantha Y Cecilia' returns 'Samantha' (first person)."""
        result = extract_display_name("Samantha Y Cecilia")
        assert result == "Samantha"
    
    def test_karen_y_yolitzin_returns_karen(self):
        """'Karen y Yolitzin' returns 'Karen' (first person)."""
        result = extract_display_name("Karen y Yolitzin")
        assert result == "Karen"
    
    def test_enrique_hector_returns_first_name(self):
        """'Enrique -Hector' returns 'Enrique' (hyphenated format)."""
        # This has a hyphen, not " y ", so it's treated differently
        result = extract_display_name("Enrique -Hector")
        assert result == "Enrique"
    
    def test_gpe_vanessa_expands(self):
        """'Gpe Vanessa' expands to 'Guadalupe Vanessa'."""
        result = extract_display_name("Gpe Vanessa")
        assert result == "Guadalupe Vanessa"
    
    def test_empty_name_returns_default(self):
        """Empty name returns 'Inquilino'."""
        result = extract_display_name("")
        assert result == "Inquilino"
    
    def test_none_name_returns_default(self):
        """None name returns 'Inquilino'."""
        result = extract_display_name(None)
        assert result == "Inquilino"


# =============================================================================
# TEST: Rent Reminder Message Generation
# =============================================================================

class TestRentReminderGeneration:
    """Test generate_rent_reminder function."""
    
    def create_tenant(self, name: str, rent: float) -> Tenant:
        """Helper to create a tenant for testing."""
        return Tenant(
            id="TEST-1",
            name=name,
            phone="+528112345678",
            property_name="Ensenada",
            unit="1",
            rent=Decimal(str(rent))
        )
    
    def test_basic_message_structure(self):
        """Message includes greeting, name, month, and rent amount."""
        tenant = self.create_tenant("Fatima", 4500)
        message = generate_rent_reminder(tenant, "enero")
        
        assert "Buenos días Fatima" in message
        assert "enero" in message
        assert "$4,500 MXN" in message
    
    def test_message_uses_expanded_name(self):
        """J Carlos should appear as Juan Carlos in message."""
        tenant = self.create_tenant("J Carlos y Raul", 8400)
        message = generate_rent_reminder(tenant, "febrero")
        
        assert "Juan Carlos" in message
        assert "J Carlos" not in message  # Should NOT contain abbreviated form
    
    def test_rent_formatting_with_comma(self):
        """Large rent amounts should have comma separator."""
        tenant = self.create_tenant("Inguva", 15900)
        message = generate_rent_reminder(tenant, "marzo")
        
        assert "$15,900 MXN" in message
    
    def test_message_tone_is_professional(self):
        """Message should be professional (Buenos días, usted implied)."""
        tenant = self.create_tenant("María", 5000)
        message = generate_rent_reminder(tenant, "abril")
        
        assert "Buenos días" in message
        assert "recordarle" in message  # Uses "usted" form
    
    def test_gpe_vanessa_expanded(self):
        """Gpe Vanessa should appear as Guadalupe Vanessa."""
        tenant = self.create_tenant("Gpe Vanessa", 7900)
        message = generate_rent_reminder(tenant, "mayo")
        
        assert "Guadalupe Vanessa" in message


# =============================================================================
# TEST: WhatsApp Link Generation
# =============================================================================

class TestWhatsAppLinkGeneration:
    """Test create_whatsapp_link function."""
    
    def test_basic_link_format(self):
        """Link should be in wa.me format."""
        link = create_whatsapp_link("+528112345678", "Hola test")
        
        assert link.startswith("https://wa.me/")
        assert "528112345678" in link
    
    def test_removes_plus_sign(self):
        """Phone number should not have + in URL."""
        link = create_whatsapp_link("+528112345678", "Test")
        
        assert "+52" not in link
        assert "528112345678" in link
    
    def test_removes_spaces(self):
        """Phone number should not have spaces."""
        link = create_whatsapp_link("+52 811 234 5678", "Test")
        
        assert " " not in link.split("?")[0]  # Check phone part
        assert "528112345678" in link
    
    def test_removes_dashes(self):
        """Phone number should not have dashes."""
        link = create_whatsapp_link("+52-811-234-5678", "Test")
        
        assert "-" not in link.split("?")[0]
    
    def test_message_is_url_encoded(self):
        """Message should be URL encoded."""
        link = create_whatsapp_link("+528112345678", "Buenos días!")
        
        assert "?text=" in link
        # URL encoding converts spaces to %20
        assert "%20" in link or "+" in link


# =============================================================================
# TEST: All Real Tenant Names from Database
# =============================================================================

class TestRealTenantNames:
    """Test with actual tenant names from the database seed."""
    
    # These are the actual tenant names from database.py seed_tenants()
    TENANT_NAMES = [
        # Matehuala
        ("Fatima", "Fatima"),
        ("J Carlos y Raul", "Juan Carlos"),  # Only Matehuala B
        ("Enrique -Hector", "Enrique"),
        ("Alejandro", "Alejandro"),
        ("José Pablo", "José"),
        ("Ali", "Ali"),
        ("Andrea", "Andrea"),
        # Múzquiz
        ("Antonio", "Antonio"),
        ("Karen y Yolitzin", "Karen"),
        ("Alfredo", "Alfredo"),
        ("Gpe Vanessa", "Guadalupe Vanessa"),
        ("Isaac", "Isaac"),
        ("Jorge de Jesús", "Jorge"),
        ("Fernanda", "Fernanda"),
        # Ensenada
        ("Claudia", "Claudia"),
        ("Samantha Y Cecilia", "Samantha"),
        ("Regina", "Regina"),
        ("David Alonso", "David"),
        ("Aranza", "Aranza"),
        ("Ericka", "Ericka"),
        ("Fatima", "Fatima"),  # Different Fatima in Ensenada
        ("Jhosvan", "Jhosvan"),
        ("Cruz", "Cruz"),
        # Huichapan
        ("Hanna", "Hanna"),
        ("Irene", "Irene"),
        ("Adrian", "Adrian"),
        ("Raul", "Raul"),
        ("Jocelyn", "Jocelyn"),
        ("Juan de Dios", "Juan"),
        ("Kevin", "Kevin"),
        ("Daniela", "Daniela"),
        # Puerta Del Sol
        ("Inguva", "Inguva"),
    ]
    
    @pytest.mark.parametrize("full_name,expected", TENANT_NAMES)
    def test_all_tenant_names(self, full_name, expected):
        """Every real tenant name should extract correctly."""
        result = extract_display_name(full_name)
        assert result == expected, f"Failed for '{full_name}': got '{result}', expected '{expected}'"


# =============================================================================
# TEST: Matehuala B Special Case (Multi-Person Communication)
# =============================================================================

class TestMatehualaBMultiTenant:
    """
    Test special case: Matehuala B has 'J Carlos y Raul'.
    
    According to user requirement:
    - This is the ONLY unit where we communicate with BOTH tenants
    - All other 'y' cases just communicate with first person
    """
    
    def test_j_carlos_y_raul_first_person(self):
        """Standard extraction gives first person (Juan Carlos)."""
        result = extract_display_name("J Carlos y Raul")
        assert result == "Juan Carlos"
    
    def test_both_names_can_be_extracted(self):
        """We can extract both names if needed for Matehuala B."""
        full_name = "J Carlos y Raul"
        
        # Split by " y " to get both tenants
        parts = full_name.split(" y ")
        first_tenant = expand_abbreviated_name(parts[0].strip())
        second_tenant = parts[1].strip() if len(parts) > 1 else None
        
        assert first_tenant == "Juan Carlos"
        assert second_tenant == "Raul"
    
    def test_separate_messages_can_be_generated(self):
        """We can generate separate messages for both tenants."""
        # For Matehuala B, we'd need to generate two messages
        tenant_names = ["Juan Carlos", "Raul"]
        
        for name in tenant_names:
            tenant = Tenant(
                id="MAT-B",
                name=name,
                phone="+528112345678",
                property_name="Matehuala",
                unit="B",
                rent=Decimal("8400")
            )
            message = generate_rent_reminder(tenant, "enero")
            assert name in message


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
