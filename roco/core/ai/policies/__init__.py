from .cixiyi import CixiyiPolicy
from .clawdragon import ClawdragonPolicy
from .flora import FloraPolicy
from .jifangfang import JifangfangPolicy
from .starweaver import StarweaverPolicy
from .steamdragon import SteamdragonPolicy
from .extended import (
    BahamutPolicy,
    ChaoslingPolicy,
    CuidingPolicy,
    DaermaoPolicy,
    DeerlePolicy,
    EmozhanshiPolicy,
    FanyingPolicy,
    GuaguaPolicy,
    GuifashiPolicy,
    HuxianPolicy,
    ParsasPolicy,
    QiukaPolicy,
    ShengyuPolicy,
    TengjiaoPolicy,
    TitaPolicy,
    XiaozongPolicy,
)

POLICY_BY_TEMPLATE = {
    FloraPolicy.template_id: FloraPolicy(),
    ClawdragonPolicy.template_id: ClawdragonPolicy(),
    StarweaverPolicy.template_id: StarweaverPolicy(),
    SteamdragonPolicy.template_id: SteamdragonPolicy(),
    JifangfangPolicy.template_id: JifangfangPolicy(),
    CixiyiPolicy.template_id: CixiyiPolicy(),
    ParsasPolicy.template_id: ParsasPolicy(),
    ChaoslingPolicy.template_id: ChaoslingPolicy(),
    QiukaPolicy.template_id: QiukaPolicy(),
    FanyingPolicy.template_id: FanyingPolicy(),
    TitaPolicy.template_id: TitaPolicy(),
    CuidingPolicy.template_id: CuidingPolicy(),
    GuaguaPolicy.template_id: GuaguaPolicy(),
    GuifashiPolicy.template_id: GuifashiPolicy(),
    BahamutPolicy.template_id: BahamutPolicy(),
    DaermaoPolicy.template_id: DaermaoPolicy(),
    HuxianPolicy.template_id: HuxianPolicy(),
    ShengyuPolicy.template_id: ShengyuPolicy(),
    DeerlePolicy.template_id: DeerlePolicy(),
    TengjiaoPolicy.template_id: TengjiaoPolicy(),
    EmozhanshiPolicy.template_id: EmozhanshiPolicy(),
    XiaozongPolicy.template_id: XiaozongPolicy(),
}

__all__ = ["POLICY_BY_TEMPLATE"]
