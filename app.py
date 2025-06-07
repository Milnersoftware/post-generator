from flask import Flask, render_template_string, request, session
import random
from datetime import datetime
import re
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

TEMPLATE = '''
<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Post-Generator: Google Maps & Facebook</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light d-flex flex-column min-vh-100">
<div class="container py-4 flex-grow-1">
    <h1 class="mb-4">Post-Generator: <span class="text-primary">Google Maps</span> & <span class="text-info">Facebook</span></h1>

    <form method="POST" class="row g-3 mb-4" autocomplete="off">
        <div class="col-md-2">
            <label for="company" class="form-label">Firmenname</label>
            <input type="text" class="form-control" id="company" name="company" required value="{{ formdata.company or '' }}">
        </div>
        <div class="col-md-2">
            <label for="city" class="form-label">Stadt</label>
            <input type="text" class="form-control" id="city" name="city" required value="{{ formdata.city or '' }}">
        </div>
        <div class="col-md-2">
            <label for="service" class="form-label">Branche/Dienstleistung</label>
            <input type="text" class="form-control" id="service" name="service" required value="{{ formdata.service or '' }}">
        </div>
        <div class="col-md-3">
            <label for="extra" class="form-label">Zusätzliche Info/Angebot (optional)</label>
            <input type="text" class="form-control" id="extra" name="extra" value="{{ formdata.extra or '' }}">
        </div>
        <div class="col-md-3">
            <label for="post_type" class="form-label">Post-Typ wählen</label>
            <select class="form-select" id="post_type" name="post_type">
                <option value="maps" {% if formdata.post_type == 'maps' %}selected{% endif %}>Google Maps</option>
                <option value="facebook" {% if formdata.post_type == 'facebook' %}selected{% endif %}>Facebook</option>
            </select>
        </div>
        <div class="col-12">
            <button type="submit" class="btn btn-success">Post generieren</button>
        </div>
    </form>

    <div class="alert alert-info">
        <strong>Google-Business-Richtlinien für Posts:</strong>
        <ul>
            <li>Keine Telefonnummern, E-Mails oder externe Links einfügen.</li>
            <li>Keine übertriebenen Werbesprüche ("bester", "Top1", "kostenlos", "100% billigster Preis").</li>
            <li>Keine Aufforderung zu Bewertungen gegen Belohnung.</li>
            <li>Keine Preise, persönliche Daten, unzulässigen Angebote.</li>
            <li>Keine Beleidigungen, Angriffe auf die Konkurrenz.</li>
        </ul>
        <b>Was mag Google?</b>
        <ul>
            <li>Klarheit, lokale Infos ("im Zentrum von Berlin", "in Düsseldorf")</li>
            <li>Neues aus dem Unternehmen, Tipps, echte Infos</li>
            <li>Handlungsaufforderung: "Jetzt kontaktieren", "Vorbeischauen" (ohne Link/Telefon)</li>
        </ul>
    </div>

    {% if post %}
    <div class="alert alert-primary">
        <h5>Generierter Post: <span class="badge bg-secondary">{{ post_type|capitalize }}</span></h5>
        <div style="white-space:pre-line; font-size:1.1rem;">{{ post }}</div>
        <button class="btn btn-outline-secondary btn-sm mt-2" onclick="navigator.clipboard.writeText(`{{ post }}`)">In die Zwischenablage kopieren</button>
        {% if post_warning %}
            <div class="alert alert-warning mt-2">
                <b>Achtung!</b> {{ post_warning }}
            </div>
        {% endif %}
    </div>
    {% endif %}

    <h4 class="mt-5 mb-3">Verlauf deiner generierten Posts:</h4>
    {% if history %}
        <table class="table table-bordered table-striped">
            <thead class="table-secondary">
                <tr>
                    <th>Datum</th>
                    <th>Typ</th>
                    <th>Firma</th>
                    <th>Stadt</th>
                    <th>Branche</th>
                    <th>Post</th>
                </tr>
            </thead>
            <tbody>
            {% for p in history %}
                <tr>
                    <td>{{ p.date }}</td>
                    <td><span class="badge bg-secondary">{{ p.post_type|capitalize }}</span></td>
                    <td>{{ p.company }}</td>
                    <td>{{ p.city }}</td>
                    <td>{{ p.service }}</td>
                    <td style="white-space: pre-line;">{{ p.text }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    {% else %}
        <div class="alert alert-light">Noch keine Posts generiert.</div>
    {% endif %}

    <div class="alert alert-success mt-4">
        <h5 class="mb-2">Wie kommst du bei Google Maps nach oben?</h5>
        <ul class="mb-2">
            <li>Regelmäßig Fotos aus deinem Standort posten (keine Stock-Fotos!)</li>
            <li>Beschreibe deine Bilder und Posts mit lokalen Begriffen (z.B. <b>{{ formdata.city }}</b>, <b>{{ formdata.service }}</b>)</li>
            <li>Sei aktiv – Profil jede Woche aktualisieren!</li>
        </ul>
        <b>Willst du wie <span style="white-space:nowrap;">Entrümpelung Mönchengladbach hadico.de</span> in die TOP 3 bei Google?<br>
        Kontaktiere uns für professionelle Google-Maps-&-SEO-Unterstützung!</b>
    </div>
</div>
<footer class="bg-dark text-white text-center py-3 mt-auto small">
    Umsetzung: 
    <a href="https://milnerwebdesign.com/" class="text-warning" target="_blank" rel="noopener">milnerwebdesign.com</a> &nbsp;|&nbsp;
    Webapps & Software: 
    <a href="https://milnersoftware.de/" class="text-warning" target="_blank" rel="noopener">milnersoftware.de</a>
</footer>
</body>
</html>
'''

FORBIDDEN = [
    r'\d{3,}',  # Telefonnummern
    r'@',  # E-Mails
    r'http[s]?://',  # Links
    'kostenlos', 'bester', 'top1', '100% billigster preis', 'bewertung abgeben', 'beleidigung', 'konkurrenz', 'rabatt'
]

def generate_post_maps(company, city, service, extra=''):
    templates = [
        f"{company} ist Ihr regionaler Experte für {service} in {city}. Wir stehen für Qualität und Kundenzufriedenheit. Kontaktieren Sie uns direkt über Google für mehr Informationen. {extra}",
        f"Neues Angebot bei {company}: {service} jetzt für Kunden aus {city}! Aktuelle Infos immer auf unserem Google-Profil. {extra}",
        f"{company} aus {city} – Ihr Partner für {service}. Wir setzen auf Professionalität und individuelle Beratung. Wir freuen uns auf Ihre Kontaktaufnahme! {extra}",
        f"Sie suchen eine zuverlässige Firma für {service} in {city}? {company} steht für Erfahrung und Vertrauen. Stellen Sie uns Ihre Fragen direkt über Google! {extra}",
        f"{company} informiert: Neue Öffnungszeiten und {service} jetzt für Kunden aus {city} verfügbar. Folgen Sie uns auf Google Maps für weitere Neuigkeiten. {extra}",
        f"Brauchen Sie Rat von einem Experten für {service} in {city}? {company} ist für Sie da – kontaktieren Sie uns direkt über Google. {extra}"
    ]
    post = random.choice(templates).replace("  ", " ").strip()
    post = re.sub(r'(\. )+', '. ', post)
    return post

def generate_post_facebook(company, city, service, extra=''):
    templates = [
        f"🎉 {company} aus {city} – dein Ansprechpartner für {service}! 🚀\n\nLerne uns kennen: Seit Jahren betreuen wir Kunden in {city} rund um {service}. Für uns zählen Qualität und persönliche Beratung.\n\n{extra}\n\nFragen? Kommentiere oder schreib uns direkt auf Facebook! 👇\n#facebook #unternehmen #lokal #{service.replace(' ', '')}",
        f"Wusstest du, dass {company} in {city} {service} anbietet? Wir setzen auf Schnelligkeit, Freundlichkeit und Zuverlässigkeit. 😊\n{extra}\n\nUnterstütze lokale Firmen – folge uns für aktuelle Neuigkeiten!\n#facebook #lokal #unternehmen #{city.replace(' ', '')} #{service.replace(' ', '')}",
        f"Auf der Suche nach einem Experten für {service} in {city}? Du bist fündig geworden! {company} ist dein kompetentes Team, immer für dich da. 💪\n{extra}\n\nSchreib uns direkt – wir beraten dich gern!\n#firma #{city.replace(' ', '')} #{service.replace(' ', '')}",
        f"Wir unterstützen {city} als zuverlässiger Partner für {service}. {company} – das ist Vertrauen, Erfahrung und Engagement. Schau dir unsere neuesten Projekte an und überzeuge dich selbst! 😍\n{extra}\n\nKommentiere, teile und bleib auf dem Laufenden!\n#dienstleistung #zufriedenheit #lokal #{city.replace(' ', '')} #{service.replace(' ', '')}",
        f"Jetzt neu: {company} erweitert das Angebot um {service} in {city}. Lerne unser Team kennen und überzeuge dich von unserem Service. 🤝\n{extra}\n\nMehr erfahren? Nachricht an uns oder kommentiere hier!\n#neu #facebook #unternehmen #{city.replace(' ', '')} #{service.replace(' ', '')}"
    ]
    post = random.choice(templates).replace("  ", " ").strip()
    post = re.sub(r'(\. )+', '. ', post)
    return post

def check_forbidden(text):
    text_lower = text.lower()
    for rule in FORBIDDEN:
        if re.search(rule, text_lower):
            return "Der Post könnte Inhalte enthalten, die gegen die Google-Richtlinien verstoßen (z.B. Telefonnummer, E-Mail, Link oder unzulässige Phrasen). Bitte prüfe deinen Text!"
    return ""

@app.route('/', methods=['GET', 'POST'])
def index():
    formdata = {'company': '', 'city': '', 'service': '', 'extra': '', 'post_type': 'maps'}
    post = ''
    post_warning = ''
    post_type = 'maps'
    if 'history' not in session:
        session['history'] = []

    if request.method == 'POST':
        company = request.form.get('company', '').strip()
        city = request.form.get('city', '').strip()
        service = request.form.get('service', '').strip()
        extra = request.form.get('extra', '').strip()
        post_type = request.form.get('post_type', 'maps')
        formdata = {'company': company, 'city': city, 'service': service, 'extra': extra, 'post_type': post_type}

        if company and city and service:
            if post_type == 'maps':
                post = generate_post_maps(company, city, service, extra)
                post_warning = check_forbidden(post)
            else:
                post = generate_post_facebook(company, city, service, extra)
                post_warning = ''  # für Facebook weniger streng prüfen
            new_item = {
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'post_type': post_type,
                'company': company,
                'city': city,
                'service': service,
                'text': post
            }
            history = session.get('history', [])
            if not any(p['text'] == post and p['post_type'] == post_type for p in history):
                history.insert(0, new_item)
                session['history'] = history

    history = session.get('history', [])
    return render_template_string(TEMPLATE, formdata=formdata, post=post, post_type=post_type,
                                  post_warning=post_warning, history=history)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
