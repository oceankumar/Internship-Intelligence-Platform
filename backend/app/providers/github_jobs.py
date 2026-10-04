from itertools import zip_longest
from app.providers.base import Provider
from app.models import SourceName
from app.providers.tracker_tables import parse_tracker, date_value


class GitHubJobsProvider(Provider):
    source = SourceName.github_jobs

    async def discover(self, query, limit):
        batches = []
        async with self.client() as client:
            for url in self.settings.github_tracker_urls:
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    batches.append(parse_tracker(response.text, url, self.source, query, limit, self.warnings))
                except Exception:
                    self.warnings.append("Tracker fetch or parsing failed: " + url)
        return [job for group in zip_longest(*batches) for job in group if job][:limit]

    def _parse_date_string(self, value):
        return date_value(value)
