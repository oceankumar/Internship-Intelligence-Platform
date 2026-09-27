from app.config import Settings
from app.models import SourceName
from app.providers.base import Provider
from app.providers.remoteok import RemoteOKProvider
from app.providers.wellfound import WellfoundProvider
from app.providers.work_at_startup import WorkAtAStartupProvider
from app.providers.yc_jobs import YCJobsProvider
from app.providers.simplify_jobs import SimplifyJobsProvider
from app.providers.github_jobs import GitHubJobsProvider
from app.providers.public_datasets import PublicDatasetsProvider
from app.providers.startup_career_pages import StartupCareerPagesProvider


def get_providers(settings: Settings, sources: list[SourceName] | None = None) -> list[Provider]:
    available: dict[SourceName, type[Provider]] = {
        SourceName.remoteok: RemoteOKProvider,
        SourceName.yc_jobs: YCJobsProvider,
        SourceName.work_at_a_startup: WorkAtAStartupProvider,
        SourceName.wellfound: WellfoundProvider,
        SourceName.simplify_jobs: SimplifyJobsProvider,
        SourceName.github_jobs: GitHubJobsProvider,
        SourceName.public_datasets: PublicDatasetsProvider,
        SourceName.startup_career_pages: StartupCareerPagesProvider,
    }
    selected = sources if sources is not None else [s for s in available if s not in {SourceName.wellfound, SourceName.work_at_a_startup}]
    return [available[source](settings) for source in selected]
