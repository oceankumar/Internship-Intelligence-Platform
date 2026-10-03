import re

COUNTRIES = {
    "India": r"india|bengaluru|bangalore|mumbai|delhi|hyderabad|pune",
    "United States": r"united states|usa|u\.s\.|(?-i:US)|san francisco|new york|seattle|austin,? tx",
    "Canada": r"canada|toronto|vancouver|montreal",
    "United Kingdom": r"united kingdom|\bUK\b|london",
    "Germany": r"germany|berlin|munich",
    "Australia": r"australia|sydney|melbourne",
    "Singapore": r"singapore",
    "France": r"france|paris",
}
REGIONS = {"APAC": {"India", "Australia", "Singapore"}, "EMEA": {"United Kingdom", "Germany", "France"}, "North America": {"United States", "Canada"}}


def countries_in(text: str) -> list[str]:
    return [name for name, pattern in COUNTRIES.items() if re.search(rf"\b(?:{pattern})\b", text, re.I)]


def canonical_country(value: str) -> str:
    return next(iter(countries_in(value)), value.strip())


def extract_geography(job):
    text = f"{job.location or ''}. {job.description}"
    locations = countries_in(job.location or "")
    job.country = locations[0] if len(locations) == 1 else None
    job.worldwide_remote = bool(re.search(r"\b(?:globally remote|remote worldwide|worldwide remote|remote anywhere|work from anywhere)\b", text, re.I) or (job.remote_status == "remote" and re.search(r"\bworldwide\b", job.location or "", re.I)))
    restrictions = []
    for sentence in re.split(r"[.;\n]", text):
        if re.search(r"remote|only|must (?:reside|be based)|based in|located in", sentence, re.I):
            restrictions.extend(countries_in(sentence))
    job.remote_countries = sorted(set(restrictions or (locations if job.remote_status == "remote" else [])))
    job.remote_regions = [region for region in REGIONS if re.search(rf"\b{region}\b", text, re.I)]
    job.authorization_required = bool(re.search(r"work authori[sz]ation|authori[sz]ed to work|citizens? only|no visa sponsorship", text, re.I))
    zone = re.search(r"(?:UTC|GMT)\s*[+-]\s*\d{1,2}|(?:overlap|working hours)[^.]{0,70}(?:timezone|time zone|EST|PST|CET|IST)", text, re.I)
    job.timezone_restriction = zone[0] if zone else None
    return job
