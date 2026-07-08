"""Onboarding: turn a fresh Supabase auth user into a usable demo advisor.

TEMPORARY — hackathon self-signup only (see docs/decisions.md and
``settings.hackathon_signup_enabled``). The permanent design is admin-only alta
of advisors (no self-signup); this whole module, the ``/api/bootstrap`` endpoint
and the flag can be deleted after the event.

Why it exists: in this domain an advisor is useless without a holding + plots +
equipment (records belong to the HOLDING, and the voice flow resolves the
dictated plot/equipment aliases). A judge who just signed up would otherwise land
in an empty app. So the first authenticated call provisions a personal sandbox
seeded to match the spec's canonical demo audio:

    "Finca de Pepe, Abamectina 1.5 litros por hectárea, araña roja, tractor"

so grabbing that exact note at the stand resolves the plot ("Finca de Pepe") and
the equipment ("tractor") with no setup. The product (Abamectina) lives in the
shared MAPA catalog and is NOT seeded here — the catalog must already carry it.
"""

from app.core.domain.models import Advisor, Equipment, Holding, Plot
from app.core.ports.repository import Repository


class OnboardingService:
    def __init__(self, repository: Repository) -> None:
        self._repo = repository

    async def bootstrap_demo_advisor(self, auth_user_id, email: str | None) -> Advisor:
        """Provision (idempotently) the advisor + demo sandbox for a new user.

        Idempotent so it is safe to call on every "just signed up" render and on
        a retry after a flaky insert: if this Supabase user already maps to an
        advisor, we return that row untouched and seed nothing.
        """
        existing = await self._repo.get_advisor_by_auth_user_id(auth_user_id)
        if existing is not None:
            return existing

        # A short slice of the auth user id keeps the demo ROPO/NIF/REA numbers
        # unique across judges, so a UNIQUE constraint never rejects a second
        # signup. Not real official numbers — it is throwaway demo data.
        suffix = str(auth_user_id).split("-")[0]  # 8 hex chars
        display_name = _name_from_email(email)

        advisor = await self._repo.save_advisor(
            Advisor(
                full_name=display_name,
                dni=f"DEMO{suffix}",
                ropo_number=f"DEMO-ASE-{suffix}",
                # ACTIVE so the registration pipeline's account_status check
                # passes and the judge can record immediately.
                account_status="ACTIVE",
                auth_user_id=auth_user_id,
            )
        )

        holding = await self._repo.save_holding(
            Holding(
                advisor_id=advisor.id,
                owner_name="Pepe García (demo)",
                # A distinct NIF from the advisor's DNI — the owner and the
                # advisor are different people. Neither is UNIQUE except the
                # advisor's DNI, so only that one strictly needs the suffix.
                owner_nif=f"NIF{suffix}",
                rea_regepa_number=f"DEMO-REA-{suffix}",
                # If nobody says who applies, the owner does (spec §5).
                default_operator_name="Pepe García",
                default_operator_ropo=f"DEMO-APL-{suffix}",
            )
        )

        # Plot 1 matches the canonical demo audio alias exactly. Citrus, because
        # "araña roja" (Tetranychus) on cítricos is the textbook case. lat/lon is
        # the enclosure centroid (Castellón) — the AEMET fallback when a phone
        # gives no GPS at execution (hard rule 8).
        await self._repo.save_plot(
            Plot(
                holding_id=holding.id,
                voice_alias="Finca de Pepe",
                crop="Cítricos",
                variety="Naranjo",
                enclosure_area_ha=2.5,
                sigpac_province="12",
                sigpac_municipality="040",
                sigpac_polygon="7",
                sigpac_parcel="15",
                sigpac_enclosure="1",
                lat=39.986,
                lon=-0.051,
            )
        )
        # A second plot so the demo history/validation screens are not single-row.
        await self._repo.save_plot(
            Plot(
                holding_id=holding.id,
                voice_alias="El Bancal",
                crop="Olivar",
                variety="Picual",
                enclosure_area_ha=1.8,
                sigpac_province="12",
                sigpac_municipality="040",
                sigpac_polygon="7",
                sigpac_parcel="22",
                sigpac_enclosure="3",
                lat=39.991,
                lon=-0.047,
            )
        )

        # Equipment alias matches the demo audio ("tractor"). ITEAF date left
        # unset (None) so the execution flow does not spuriously warn; the stand
        # demo is about the happy path.
        await self._repo.save_equipment(
            Equipment(
                holding_id=holding.id,
                equipment_alias="tractor",
                equipment_type="TRACTOR",
                roma_number=f"DEMO-ROMA-{suffix}",
            )
        )

        return advisor


def _name_from_email(email: str | None) -> str:
    """A friendly display name from the signup email's local part.

    "jose.perez@gmail.com" -> "Jose Perez". Falls back to a generic label when
    there is no usable email (demo data, never shown on a legal document
    unedited)."""
    if not email or "@" not in email:
        return "Asesor Demo"
    local = email.split("@", 1)[0]
    words = [w for w in local.replace(".", " ").replace("_", " ").split() if w]
    return " ".join(w.capitalize() for w in words) or "Asesor Demo"
