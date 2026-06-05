from app.config import Settings
from app.models import SourceName
from app.providers.base import Provider
from app.providers.remoteok import RemoteOKProvider
from app.providers.wellfound import WellfoundProvider
from app.providers.work_at_startup import WorkAtAStartupProvider
from app.providers.yc_jobs import YCJobsProvider


def get_providers(settings: Settings, sources: list[SourceName] | None = None) -> list[Provider]:
    available: dict[SourceName, type[Provider]] = {
        SourceName.remoteok: RemoteOKProvider,
        SourceName.yc_jobs: YCJobsProvider,
        SourceName.work_at_a_startup: WorkAtAStartupProvider,
        SourceName.wellfound: WellfoundProvider,
    }
    selected = sources or list(available.keys())
    return [available[source](settings) for source in selected]

