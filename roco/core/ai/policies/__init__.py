from .clawdragon import ClawdragonPolicy
from .flora import FloraPolicy
from .starweaver import StarweaverPolicy
from .steamdragon import SteamdragonPolicy

POLICY_BY_TEMPLATE = {
    FloraPolicy.template_id: FloraPolicy(),
    ClawdragonPolicy.template_id: ClawdragonPolicy(),
    StarweaverPolicy.template_id: StarweaverPolicy(),
    SteamdragonPolicy.template_id: SteamdragonPolicy(),
}

__all__ = ["POLICY_BY_TEMPLATE"]
