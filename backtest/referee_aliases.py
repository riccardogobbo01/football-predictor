"""
Alias ESPLICITI arbitro football-data.org -> chiave canonica (nome Transfermarkt normalizzato, vedi backtest/referees.normalize).
Chiave dell'alias: (campionato football-data.co.uk, nome dell'arbitro in football-data.org normalizzato). Un arbitro senza storico
(debutto in prima divisione dopo il 2016/17, o nome non presente in Transfermarkt) ha come chiave canonica il proprio nome normalizzato:
il suo effetto è zero finché non accumula partite. Elenco compilato sugli arbitri indicati da football-data.org nel 2026/27 (111 nomi).
"""

REFEREE_ALIASES = {
    "I1": {
        "alberto arena": "alberto ruben arena",   # Alberto Arena
        "andrea colombo": "andrea colombo",   # Andrea Colombo
        "antonio rapuano": "antonio rapuano",   # Antonio Rapuano
        "claudio allegretta": "claudio allegretta",   # Claudio Allegretta
        "daniele chiffi": "daniele chiffi",   # Daniele Chiffi
        "daniele doveri": "daniele doveri",   # Daniele Doveri
        "daniele perenzoni": "daniele perenzoni",   # Daniele Perenzoni
        "davide di marco": "davide di marco",   # Davide Di Marco
        "davide massa": "davide massa",   # Davide Massa
        "ermanno feliciani": "ermanno feliciani",   # Ermanno Feliciani
        "fabio maresca": "fabio maresca",   # Fabio Maresca
        "federico la penna": "federico la penna",   # Federico La Penna
        "francesco fourneau": "francesco fourneau",   # Francesco Fourneau
        "gianluca manganiello": "gianluca manganiello",   # Gianluca Manganiello
        "giovanni ayroldi": "giovanni ayroldi",   # Giovanni Ayroldi
        "giuseppe collu": "giuseppe collu",   # Giuseppe Collu
        "giuseppe mucera": "giuseppe mucera",   # Giuseppe Mucera
        "juan luca sacchi": "juan luca sacchi",   # Juan Luca Sacchi
        "kevin bonacina": "kevin bonacina",   # Kevin Bonacina
        "livio marinelli": "livio marinelli",   # Livio Marinelli
        "luca pairetto": "luca pairetto",   # Luca Pairetto
        "luca zufferli": "luca zufferli",   # Luca Zufferli
        "marco di bello": "marco di bello",   # Marco Di Bello
        "marco guida": "marco guida",   # Marco Guida
        "mario perri": "mario perri",   # Mario Perri
        "matteo marcenaro": "matteo marcenaro",   # Matteo Marcenaro
        "maurizio mariani": "maurizio mariani",   # Maurizio Mariani
        "michael fabbri": "michael fabbri",   # Michael Fabbri
        "paride tremolada": "paride tremolada",   # Paride Tremolada
        "simone sozza": "simone sozza",   # Simone Sozza
        "valerio crezzini": "valerio crezzini",   # Valerio Crezzini
    },
    "E0": {
        "adam herczeg": "adam herczeg",   # Adam Herczeg
        "adrian gillett": "adrian gillett",   # Adrian Gillett
        "andy madley": "andrew madley",   # Andy Madley
        "chris kavanagh": "chris kavanagh",   # Chris Kavanagh
        "craig pawson": "craig pawson",   # Craig Pawson
        "darren england": "darren england",   # Darren England
        "farai hallam": "farai hallam",   # Farai Hallam
        "jarred gillett": "jarred gillett",   # Jarred Gillett
        "john brooks": "john brooks",   # John Brooks
        "joshua smith": "josh smith",   # Joshua Smith
        "lewis smith": "lewis smith",   # Lewis Smith
        "michael oliver": "michael oliver",   # Michael Oliver
        "michael salisbury": "michael salisbury",   # Michael Salisbury
        "paul tierney": "paul tierney",   # Paul Tierney
        "peter bankes": "peter bankes",   # Peter Bankes
        "robert jones": "robert jones",   # Robert Jones
        "sam barrott": "samuel barrott",   # Sam Barrott
        "stuart attwell": "stuart attwell",   # Stuart Attwell
        "thomas bramall": "thomas bramall",   # Thomas Bramall
        "tony harrington": "tony harrington",   # Tony Harrington
    },
    "D1": {
        "bastian dankert": "bastian dankert",   # Bastian Dankert
        "benjamin brand": "benjamin brand",   # Benjamin Brand
        "christian dingert": "christian dingert",   # Christian Dingert
        "daniel schlager": "daniel schlager",   # Daniel Schlager
        "daniel siebert": "daniel siebert",   # Daniel Siebert
        "felix zwayer": "felix zwayer",   # Felix Zwayer
        "florian badstubner": "florian badstubner",   # Florian Badstübner
        "florian exner": "florian exner",   # Florian Exner
        "harm osmers": "harm osmers",   # Harm Osmers
        "martin petersen": "martin petersen",   # Martin Petersen
        "matthias jollenbeck": "matthias jollenbeck",   # Matthias Jöllenbeck
        "max burda": "max burda",   # Max Burda
        "richard hempel": "richard hempel",   # Richard Hempel
        "robert hartmann": "robert hartmann",   # Robert Hartmann
        "robert schroder": "robert schroder",   # Robert Schröder
        "robin braun": "robin braun",   # Robin Braun
        "sascha stegemann": "sascha stegemann",   # Sascha Stegemann
        "soren storks": "soren storks",   # Sören Storks
        "sven jablonski": "sven jablonski",   # Sven Jablonski
        "timo gerach": "timo gerach",   # Timo Gerach
        "tobias reichel": "tobias reichel",   # Tobias Reichel
        "tobias stieler": "tobias stieler",   # Tobias Stieler
    },
    "SP1": {
        "adrian cordero vega": "adrian cordero vega",   # Adrián Cordero Vega
        "alejandro hernandez hernandez": "alejandro hernandez hernandez",   # Alejandro Hernández Hernández
        "alejandro quintero gonzalez": "alejandro quintero gonzalez",   # Alejandro Quintero González
        "carlos muniz munoz": "carlos muniz munoz",   # Carlos Muñiz Muñoz
        "cesar soto grado": "cesar soto grado",   # César Soto Grado
        "francisco hernandez maeso": "francisco jose hernandez maeso",   # Francisco Hernández Maeso
        "isidro diaz de mera": "isidro diaz de mera escuderos",   # Isidro Díaz de Mera
        "javier alberola rojas": "javier alberola rojas",   # Javier Alberola Rojas
        "jesus gil manzano": "jesus gil manzano",   # Jesús Gil Manzano
        "jon gonzalez esteban": "jon gonzalez esteban",   # Jon González Esteban
        "jose munuera montero": "jose luis munuera montero",   # José Munuera Montero
        "jose sanchez martinez": "jose maria sanchez martinez",   # José Sánchez Martínez
        "juan martinez munuera": "juan martinez munuera",   # Juan Martínez Munuera
        "luis bestard servera": "luis bestard servera",   # Luis Bestard Servera
        "manuel orellana cid": "manuel orellana cid",   # Manuel Orellana Cid
        "mateo busquets ferrer": "mateo busquets ferrer",   # Mateo Busquets Ferrer
        "miguel chua": "miguel chua",   # Miguel Chua
        "miguel ortiz arias": "miguel angel ortiz arias",   # Miguel Ortiz Arias
        "miguel sesma espinosa": "miguel sesma espinosa",   # Miguel Sesma Espinosa
        "ricardo de burgos": "de burgos bengoetxea",   # Ricardo de Burgos
        "victor garcia verdura": "victor garcia verdura",   # Víctor García Verdura
    },
    "F1": {
        "aurelien petit": "aurelien petit",   # Aurélien Petit
        "azzedine souifi": "azzedine souifi",   # Azzedine Souifi
        "bastien dechepy": "bastien dechepy",   # Bastien Dechepy
        "clement turpin": "clement turpin",   # Clément Turpin
        "eric wattellier": "eric wattellier",   # Eric Wattellier
        "francois letexier": "francois letexier",   # François Letexier
        "geoffrey kubler": "geoffrey kubler",   # Geoffrey Kubler
        "guillaume paradis": "guillaume paradis",   # Guillaume Paradis
        "hakim ben el hadj salem": "hakim ben el hadj",   # Hakim Ben El Hadj Salem
        "jeremie pignard": "jeremie pignard",   # Jérémie Pignard
        "jeremy stinat": "jeremy stinat",   # Jeremy Stinat
        "jerome brisard": "jerome brisard",   # Jérôme Brisard
        "marc bollengier": "marc bollengier",   # Marc Bollengier
        "mathieu vernice": "mathieu vernice",   # Mathieu Vernice
        "romain lissorgue": "romain lissorgue",   # Romain Lissorgue
        "ruddy buquet": "ruddy buquet",   # Ruddy Buquet
        "willy delajod": "willy delajod",   # Willy Delajod
    },
}

# Arbitri 2026/27 senza storico nel dataset 2016/17-2025/26 (effetto zero finché non accumulano partite)
NEW_REFEREES_2026 = [
    ("I1", "Claudio Allegretta"),
    ("E0", "Adam Herczeg"),
    ("E0", "Adrian Gillett"),
    ("D1", "Richard Hempel"),
    ("SP1", "Carlos Muñiz Muñoz"),
    ("SP1", "Jon González Esteban"),
    ("SP1", "Luis Bestard Servera"),
    ("SP1", "Manuel Orellana Cid"),
    ("SP1", "Miguel Chua"),
    ("F1", "Azzedine Souifi"),
    ("F1", "Geoffrey Kubler"),
]
