"""
Projectors package — import all projector modules for auto-registration.

Each module uses ``@ProjectorRegistry.register("ResourceType")`` to register itself.
Simply importing the module is sufficient to trigger registration.
"""
# fmt: off
from . import patient             # noqa: F401
from . import condition           # noqa: F401
from . import observation         # noqa: F401
from . import encounter           # noqa: F401
from . import medication_request  # noqa: F401
from . import medication_dispense # noqa: F401
from . import allergy_intolerance # noqa: F401
from . import care_plan           # noqa: F401
from . import care_team           # noqa: F401
from . import coverage            # noqa: F401
from . import device              # noqa: F401
from . import diagnostic_report   # noqa: F401
from . import document_reference  # noqa: F401
from . import goal                # noqa: F401
from . import immunization        # noqa: F401
from . import procedure           # noqa: F401
from . import service_request     # noqa: F401
from . import specimen            # noqa: F401
from . import medication          # noqa: F401
from . import location            # noqa: F401
from . import organization        # noqa: F401
from . import practitioner        # noqa: F401  (includes PractitionerRole)
from . import related_person      # noqa: F401
from . import provenance          # noqa: F401
from . import risk_assessment     # noqa: F401
from . import media               # noqa: F401
# fmt: on
