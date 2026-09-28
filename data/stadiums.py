"""
Coordinate GPS degli stadi principali per il meteo (lat/lon, WGS84).
Aggiungere nuove squadre seguendo il formato esistente.
"""

STADIUMS: dict[str, dict] = {
    # ── Serie A ──────────────────────────────────────────────────────────────
    "Milan":            {"lat": 45.478, "lon": 9.124,  "stadium": "San Siro"},
    "Inter":            {"lat": 45.478, "lon": 9.124,  "stadium": "San Siro"},
    "Juventus":         {"lat": 45.109, "lon": 7.641,  "stadium": "Allianz Stadium"},
    "Napoli":           {"lat": 40.828, "lon": 14.193, "stadium": "Diego Armando Maradona"},
    "Roma":             {"lat": 41.934, "lon": 12.455, "stadium": "Olimpico"},
    "Lazio":            {"lat": 41.934, "lon": 12.455, "stadium": "Olimpico"},
    "Atalanta":         {"lat": 45.709, "lon": 9.677,  "stadium": "Gewiss Stadium"},
    "Fiorentina":       {"lat": 43.781, "lon": 11.283, "stadium": "Artemio Franchi"},
    "Bologna":          {"lat": 44.493, "lon": 11.310, "stadium": "Renato Dall'Ara"},
    "Torino":           {"lat": 45.042, "lon": 7.663,  "stadium": "Grande Torino"},
    "Genoa":            {"lat": 44.416, "lon": 8.952,  "stadium": "Luigi Ferraris"},
    "Sampdoria":        {"lat": 44.416, "lon": 8.952,  "stadium": "Luigi Ferraris"},
    "Udinese":          {"lat": 46.074, "lon": 13.235, "stadium": "Bluenergy Stadium"},
    "Cagliari":         {"lat": 39.207, "lon": 9.127,  "stadium": "Unipol Domus"},
    "Parma":            {"lat": 44.799, "lon": 10.325, "stadium": "Ennio Tardini"},
    "Venezia":          {"lat": 45.389, "lon": 12.195, "stadium": "Penzo"},
    "Hellas Verona":    {"lat": 45.436, "lon": 10.972, "stadium": "Marcantonio Bentegodi"},
    "Empoli":           {"lat": 43.728, "lon": 10.957, "stadium": "Carlo Castellani"},
    "Como":             {"lat": 45.810, "lon": 9.085,  "stadium": "Giuseppe Sinigaglia"},
    "Lecce":            {"lat": 40.353, "lon": 18.171, "stadium": "Via del Mare"},
    "Monza":            {"lat": 45.618, "lon": 9.295,  "stadium": "Brianteo"},

    # ── Premier League ───────────────────────────────────────────────────────
    "Arsenal":              {"lat": 51.555, "lon": -0.108, "stadium": "Emirates Stadium"},
    "Chelsea":              {"lat": 51.481, "lon": -0.191, "stadium": "Stamford Bridge"},
    "Manchester City":      {"lat": 53.483, "lon": -2.200, "stadium": "Etihad Stadium"},
    "Manchester United":    {"lat": 53.463, "lon": -2.291, "stadium": "Old Trafford"},
    "Liverpool":            {"lat": 53.430, "lon": -2.961, "stadium": "Anfield"},
    "Tottenham Hotspur":    {"lat": 51.604, "lon": -0.066, "stadium": "Tottenham Hotspur Stadium"},
    "Newcastle United":     {"lat": 54.975, "lon": -1.622, "stadium": "St. James' Park"},
    "Aston Villa":          {"lat": 52.509, "lon": -1.885, "stadium": "Villa Park"},
    "Brighton":             {"lat": 50.862, "lon": -0.083, "stadium": "Amex Stadium"},
    "West Ham":             {"lat": 51.538, "lon": -0.017, "stadium": "London Stadium"},
    "Everton":              {"lat": 53.438, "lon": -2.967, "stadium": "Goodison Park"},
    "Leicester City":       {"lat": 52.620, "lon": -1.142, "stadium": "King Power Stadium"},
    "Brentford":            {"lat": 51.490, "lon": -0.309, "stadium": "Gtech Community Stadium"},
    "Crystal Palace":       {"lat": 51.398, "lon": -0.086, "stadium": "Selhurst Park"},
    "Wolverhampton":        {"lat": 52.590, "lon": -2.130, "stadium": "Molineux Stadium"},
    "Fulham":               {"lat": 51.475, "lon": -0.222, "stadium": "Craven Cottage"},

    # ── Bundesliga ────────────────────────────────────────────────────────────
    "Bayern München":       {"lat": 48.219, "lon": 11.625, "stadium": "Allianz Arena"},
    "Borussia Dortmund":    {"lat": 51.493, "lon": 7.452,  "stadium": "Signal Iduna Park"},
    "Bayer 04 Leverkusen":  {"lat": 51.038, "lon": 7.002,  "stadium": "BayArena"},
    "RB Leipzig":           {"lat": 51.345, "lon": 12.348, "stadium": "Red Bull Arena"},
    "Eintracht Frankfurt":  {"lat": 50.069, "lon": 8.645,  "stadium": "Deutsche Bank Park"},
    "Borussia Mönchengladbach": {"lat": 51.175, "lon": 6.385, "stadium": "Borussia-Park"},
    "Stuttgart":            {"lat": 48.792, "lon": 9.232,  "stadium": "MHPArena"},
    "Werder Bremen":        {"lat": 53.066, "lon": 8.837,  "stadium": "Wohninvest Weserstadion"},
    "Freiburg":             {"lat": 47.991, "lon": 7.893,  "stadium": "Europa-Park Stadion"},
    "Wolfsburg":            {"lat": 52.432, "lon": 10.804, "stadium": "Volkswagen Arena"},

    # ── La Liga ───────────────────────────────────────────────────────────────
    "Real Madrid":          {"lat": 40.453, "lon": -3.688, "stadium": "Santiago Bernabéu"},
    "FC Barcelona":         {"lat": 41.381, "lon": 2.123,  "stadium": "Spotify Camp Nou"},
    "Atlético de Madrid":   {"lat": 40.436, "lon": -3.600, "stadium": "Cívitas Metropolitano"},
    "Sevilla":              {"lat": 37.384, "lon": -5.971, "stadium": "Ramón Sánchez-Pizjuán"},
    "Real Betis":           {"lat": 37.357, "lon": -5.981, "stadium": "Estadio Benito Villamarín"},
    "Valencia":             {"lat": 39.474, "lon": -0.358, "stadium": "Mestalla"},
    "Real Sociedad":        {"lat": 43.301, "lon": -1.974, "stadium": "Reale Arena"},
    "Villarreal":           {"lat": 39.944, "lon": -0.104, "stadium": "Estadio de la Cerámica"},
    "Athletic Club":        {"lat": 43.264, "lon": -2.950, "stadium": "Estadio de San Mamés"},
    "Celta Vigo":           {"lat": 42.212, "lon": -8.737, "stadium": "Abanca-Balaídos"},

    # ── Ligue 1 ───────────────────────────────────────────────────────────────
    "Paris Saint-Germain":  {"lat": 48.841, "lon": 2.253,  "stadium": "Parc des Princes"},
    "Olympique de Marseille": {"lat": 43.270, "lon": 5.396, "stadium": "Stade Vélodrome"},
    "Olympique Lyonnais":   {"lat": 45.765, "lon": 4.982,  "stadium": "Groupama Stadium"},
    "AS Monaco":            {"lat": 43.727, "lon": 7.416,  "stadium": "Stade Louis II"},
    "LOSC Lille":           {"lat": 50.612, "lon": 3.130,  "stadium": "Stade Pierre-Mauroy"},
    "Stade Rennais":        {"lat": 48.107, "lon": -1.714, "stadium": "Roazhon Park"},
    "Nice":                 {"lat": 43.705, "lon": 7.193,  "stadium": "Allianz Riviera"},
    "Lens":                 {"lat": 50.432, "lon": 2.815,  "stadium": "Stade Bollaert-Delelis"},
    "Strasbourg":           {"lat": 48.560, "lon": 7.752,  "stadium": "Stade de la Meinau"},
    "Montpellier":          {"lat": 43.622, "lon": 3.814,  "stadium": "Stade de la Mosson"},
}
