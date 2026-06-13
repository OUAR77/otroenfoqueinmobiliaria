import os, json, re, urllib.parse
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, func as sqlfunc
from database import Base, engine, get_db
from models.property import Property
from models.contact import ContactMessage
from models.blog import BlogPost
from models.valuation import ValuationRequest
from models.alert import SearchAlert
from config import SITE_NAME, SITE_URL, WHATSAPP_NUMBER, GROQ_API_KEY

def first_image(prop):
    """Get first image src from a property."""
    parsed = parse_images(prop.images)
    return parsed[0]["src"] if parsed else ""

Base.metadata.create_all(bind=engine)

app = FastAPI(title=SITE_NAME)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")
from starlette.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
templates.env.globals["site_url"] = SITE_URL
templates.env.globals["site_name"] = SITE_NAME
templates.env.globals["whatsapp"] = WHATSAPP_NUMBER

def jinja_first_image(raw):
    parsed = parse_images(raw)
    return parsed[0]["src"] if parsed else ""

def jinja_cover_image(prop):
    if prop.cover_image:
        return prop.cover_image
    return jinja_first_image(prop.images)

def jinja_parse_images(raw):
    return parse_images(raw)

def jinja_group_images(raw):
    parsed = parse_images(raw)
    groups = {}
    for img in parsed:
        cat = img.get("cat", "otras")
        groups.setdefault(cat, []).append(img["src"])
    result = []
    for key in CATEGORIES:
        if key in groups:
            result.append({"key": key, "label": CATEGORIES[key], "images": groups[key]})
    for cat, srcs in groups.items():
        if cat not in CATEGORIES:
            result.append({"key": cat, "label": cat.capitalize(), "images": srcs})
    return result

templates.env.filters["first_image"] = jinja_first_image
templates.env.filters["cover_image"] = jinja_cover_image
templates.env.filters["parse_images"] = jinja_parse_images
templates.env.filters["group_images"] = jinja_group_images

os.makedirs("static/properties", exist_ok=True)

CATEGORIES = {
    "salon": "Salón",
    "cocina": "Cocina",
    "dormitorio": "Dormitorios",
    "general": "General",
    "banyo": "Baños",
    "terraza": "Terraza / Exterior",
    "piscina": "Piscina",
    "garaje": "Garaje",
    "entrada": "Entrada",
    "otras": "Otras estancias",
}

def save_upload(content, filename, prop_id, cat_key):
    """Save an uploaded file, converting HEIC/HEIF to JPEG."""
    name, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext in ('.heic', '.heif'):
        import io
        from PIL import Image
        try:
            from pillow_heif import open_heif
            heif_file = open_heif(io.BytesIO(content))
            img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data)
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=92)
            content = buf.getvalue()
        except Exception:
            pass
        ext = '.jpg'
    name = re.sub(r'[^\w\s-]', '', name).strip()
    name = re.sub(r'[\s]+', '_', name)
    safe_name = name + ext
    path = f"static/properties/{prop_id}_{cat_key}_{safe_name}"
    with open(path, "wb") as out:
        out.write(content)
    return f"/static/properties/{prop_id}_{cat_key}_{safe_name}"

def parse_images(raw):
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("["):
        try:
            return json.loads(raw)
        except:
            return []
    return [{"src": img.strip(), "cat": "otras"} for img in raw.split(",") if img.strip()]

def images_to_json(images_list):
    """Convert list of {src, cat} to JSON string."""
    return json.dumps(images_list, ensure_ascii=False)

def group_images_by_category(images_list):
    """Return dict of {cat_label: [src, ...]} preserving order."""
    groups = {}
    for img in images_list:
        cat = img.get("cat", "otras")
        groups.setdefault(cat, []).append(img["src"])
    ordered = []
    for key in CATEGORIES:
        if key in groups:
            ordered.append((CATEGORIES[key], groups[key]))
    # any unrecognized categories come last
    for cat, srcs in groups.items():
        if cat not in CATEGORIES:
            ordered.append((cat, srcs))
    return ordered


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text


# --- PUBLIC ROUTES ---

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    featured = db.query(Property).filter(
        Property.featured == True,
        Property.status == "disponible"
    ).order_by(desc(Property.created_at)).limit(6).all()
    latest = db.query(Property).filter(
        Property.status == "disponible"
    ).order_by(desc(Property.created_at)).limit(3).all()
    posts = db.query(BlogPost).filter(BlogPost.published == 1).order_by(desc(BlogPost.created_at)).limit(3).all()
    return templates.TemplateResponse(request, "index.html", {"featured": featured, "latest": latest,
        "posts": posts,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
        "canonical": f"{SITE_URL}/",
        "meta_title": SITE_NAME,
        "meta_description": "Tu asesoría inmobiliaria de confianza en Huércal de Almería. Compra, venta y alquiler de propiedades en Almería, Aguadulce, Roquetas y toda la provincia.",
    })


@app.get("/propiedades", response_class=HTMLResponse)
def list_properties(
    request: Request, db: Session = Depends(get_db),
    operation: str = Query(None), tipo: str = Query(None),
    bedrooms: str = Query(None), min_price: str = Query(None),
    max_price: str = Query(None), q: str = Query(None),
):
    query = db.query(Property).filter(Property.status == "disponible")
    if operation:
        query = query.filter(Property.operation == operation)
    if tipo:
        query = query.filter(Property.property_type == tipo)
    bdrm = None
    if bedrooms and bedrooms.strip():
        try: bdrm = int(bedrooms)
        except: pass
    if bdrm:
        query = query.filter(Property.bedrooms >= bdrm)
    min_p = None
    if min_price and min_price.strip():
        try: min_p = float(min_price)
        except: pass
    if min_p:
        query = query.filter(Property.price >= min_p)
    max_p = None
    if max_price and max_price.strip():
        try: max_p = float(max_price)
        except: pass
    if max_p:
        query = query.filter(Property.price <= max_p)
    if q:
        query = query.filter(
            Property.title.contains(q) | Property.location.contains(q)
            | Property.description.contains(q)
        )
    properties = query.order_by(desc(Property.featured), desc(Property.created_at)).all()
    types = db.query(Property.property_type).distinct().all()
    return templates.TemplateResponse(request, "properties.html", {"properties": properties,
        "property_types": [t[0] for t in types],
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
        "canonical": f"{SITE_URL}/propiedades",
        "meta_title": "Propiedades en venta y alquiler en Almería",
        "meta_description": "Encuentra pisos, casas y locales en Almería, Aguadulce, Roquetas y Huércal de Almería. Compra, venta y alquiler con Otro Enfoque Inmobiliaria.",
    })


@app.get("/propiedades/{slug}", response_class=HTMLResponse)
def property_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.slug == slug).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada")
    images_list = parse_images(prop.images)
    all_srcs = [img["src"] for img in images_list]
    grouped = group_images_by_category(images_list)
    features = [f.strip() for f in prop.features.split(",")] if prop.features else []
    prop.views = (prop.views or 0) + 1
    db.commit()
    whatsapp_msg = urllib.parse.quote(f"Hola! Me interesa la propiedad: {prop.title} ({SITE_URL}/propiedades/{prop.slug})")
    return templates.TemplateResponse(request, "detail.html", {"p": prop,
        "images": all_srcs, "images_list": images_list, "grouped_images": grouped, "features": features,
        "categories": CATEGORIES,
        "whatsapp_msg": whatsapp_msg,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
        "canonical": f"{SITE_URL}/propiedades/{slug}",
        "meta_title": prop.title,
        "meta_description": f"{prop.title} en {prop.location} - {prop.bedrooms} hab, {prop.surface}m² - {prop.price:,.0f}€",
    })


# --- BLOG ---

@app.get("/blog", response_class=HTMLResponse)
def blog_list(request: Request, db: Session = Depends(get_db)):
    posts = db.query(BlogPost).filter(BlogPost.published == 1).order_by(desc(BlogPost.created_at)).all()
    return templates.TemplateResponse(request, "blog_list.html", {
        "posts": posts,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
        "canonical": f"{SITE_URL}/blog",
        "meta_title": "Blog — Otro Enfoque Inmobiliaria",
        "meta_description": "Consejos, guías y noticias sobre compra, venta y alquiler de propiedades en Almería.",
    })


@app.get("/blog/{slug}", response_class=HTMLResponse)
def blog_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    post = db.query(BlogPost).filter(BlogPost.slug == slug, BlogPost.published == 1).first()
    if not post:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    recent = db.query(BlogPost).filter(BlogPost.published == 1, BlogPost.id != post.id).order_by(desc(BlogPost.created_at)).limit(3).all()
    return templates.TemplateResponse(request, "blog_detail.html", {
        "post": post, "recent": recent,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
        "canonical": f"{SITE_URL}/blog/{slug}",
        "meta_title": f"{post.title} — Otro Enfoque Inmobiliaria",
        "meta_description": post.excerpt or post.title,
    })


# --- VALUATION ---

@app.get("/valoracion", response_class=HTMLResponse)
def valuation_form(request: Request):
    return templates.TemplateResponse(request, "valuation.html", {
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
        "canonical": f"{SITE_URL}/valoracion",
        "meta_title": "Solicita una valoración gratuita — Otro Enfoque Inmobiliaria",
        "meta_description": "Pide tu valoración online gratuita sin compromiso. Te valoramos tu piso, casa o local en Almería.",
    })


@app.post("/valoracion")
def valuation_post(
    request: Request, db: Session = Depends(get_db),
    name: str = Form(...), email: str = Form(...),
    phone: str = Form(""), property_type: str = Form(""),
    address: str = Form(""), surface: float = Form(0),
    notes: str = Form(""),
):
    if not name.strip() or not email.strip():
        return templates.TemplateResponse(request, "valuation.html", {
            "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
            "error": "Rellena nombre y email obligatorios",
        }, status_code=400)
    vr = ValuationRequest(name=name, email=email, phone=phone,
        property_type=property_type, address=address,
        surface=surface, notes=notes)
    db.add(vr)
    db.commit()
    return templates.TemplateResponse(request, "valuation.html", {
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
        "success": "Solicitud enviada correctamente. Te contactaremos pronto para tu valoración.",
    })


# --- SEARCH ALERTS ---

@app.post("/api/alert")
def create_alert(
    request: Request, db: Session = Depends(get_db),
    email: str = Form(...), name: str = Form(""),
    operation: str = Form(""), property_type: str = Form(""),
    min_price: str = Form(""), max_price: str = Form(""),
    location: str = Form(""),
):
    if not email.strip():
        return JSONResponse({"error": "Email requerido"}, status_code=400)
    existing = db.query(SearchAlert).filter(SearchAlert.email == email.strip()).first()
    if existing:
        return JSONResponse({"message": "Ya tienes una alerta activa con este email"})
    alert = SearchAlert(email=email.strip(), name=name, operation=operation,
        property_type=property_type, min_price=min_price,
        max_price=max_price, location=location)
    db.add(alert)
    db.commit()
    return JSONResponse({"message": "Alerta creada correctamente. Te avisaremos cuando haya nuevas propiedades."})


REVIEWS = [
    {"name": "Sergio", "role": "Local Guide · 28 reseñas", "text": "Sin duda el mejor trato que puedes encontrar. Nos pusimos en manos de Jose Enrique para la venta de nuestra casa y fue todo un acierto. El trato, cercanía y su buen hacer en todo momento lo dicen todo de él. Si tuviese que confiar en alguien, ellos son los indicados tanto para vender como para comprar, tus sueños ellos los pueden hacer realidad."},
    {"name": "Sofía M M", "role": "Local Guide · 19 reseñas", "text": "He hecho todas las gestiones desde Madrid con Jose Enrique, por teléfono y sin conocernos en persona. Qué amabilidad y qué profesionalidad. Da gusto encontrar personas que les gusta su trabajo y que lo único que les importa es hacerlo bien. Solo tengo palabras de agradecimiento. Después de unos meses duros, fue llamarle y ver un poco la luz. Gracias de verdad."},
    {"name": "Eva Maria Sanchez", "role": "7 reseñas", "text": "Tuvimos mucha suerte de poder vender con esta inmobiliaria. Desde el primer momento le pusieron mucha dedicación a la venta y cuidaron todo tipo de detalle. Después de buscar en muchas inmobiliarias y no tener buenos resultados, sin duda esta fue la mejor opción. Nos ayudaron en todo momento a vender y a buscar otra propiedad. Sin duda recomiendo esta inmobiliaria tanto para vender, comprar o incluso para tema bancos. Muchas gracias José Enrique y Carmen, sois los mejores profesionales que hemos conocido de este sector."},
    {"name": "Jose Manuel Molina Rueda", "role": "2 reseñas", "text": "Grandísimos profesionales. En seis meses vendieron mi casa, un trato buenísimo, disponibilidad siempre y te hacen sentir como una familia, amables y serios en su trabajo. Jose Enrique fue el contacto que me atendió con mucha profesionalidad, amabilidad y seriedad en su trabajo. Les doy un sobresaliente y mil gracias por todo, sois los mejores."},
    {"name": "Isabel María Albarracín Rivera", "role": "Local Guide · 24 reseñas", "text": "La compra de la casa de mi hijo en Viator ha sido más fácil gracias a la dedicación de Jose Enrique. Para nosotros en la distancia nos lo ha hecho muy llevadero, cada vez que lo hemos llamado nos ha atendido excepcionalmente. Creo que hemos ganado un amigo y un gran profesional al que confiaríamos plenamente la venta o compra de nuestra casa."},
    {"name": "Juan", "role": "5 reseñas", "text": "Un buen trabajo por parte de la inmobiliaria Otro Enfoque y en su cabeza José Enrique, que ha hecho el trabajo super sencillo y rápido. Gracias por todo. Volveremos a confiar en ti en próximas operaciones."},
    {"name": "ISABEL MORALES QUESADA", "role": "1 reseña", "text": "Un trato muy cercano y personalizado. Con nosotros de la mano en todo el proceso de venta. Y sobre todo valorar un nuevo concepto inmobiliario que se une a un trato inmejorable. Sin duda volvería a contar con Otro Enfoque."},
    {"name": "Cristina Garcia", "role": "4 reseñas", "text": "Estamos muy agradecidos por el trabajo de Jose Enrique. Desde el primer momento nos acompañó con profesionalidad, cercanía y una atención impecable. Nos hizo sentir tranquilos durante todo el proceso de venta, resolviendo cada gestión y duda con rapidez y claridad. Gracias por hacerlo todo tan fácil y por acompañarnos con tanta humanidad. 100% recomendable."},
    {"name": "Juanen 195", "role": "Local Guide · 40 reseñas", "text": "Unos grandes profesionales desde el principio al fin. Te ayudan en todo lo que pueden y te asesoran en lo que necesites, un trato cercano y cumplen con su palabra. En general todo muy bien y lo recomiendo."},
    {"name": "Antonio Terrones Albarracín", "role": "2 reseñas", "text": "Excelente trabajo de José Enrique. Desde el primer momento super atento y me ha facilitado mucho la compra de mi primera vivienda. Muchas gracias."},
    {"name": "Raul", "role": "5 reseñas", "text": "Un auténtico profesional, el cual sabe lo que hace y disfruta de su trabajo. He pasado por varias inmobiliarias y sin duda esta es la mejor. Cumplen con lo que dicen, están contigo en todo el proceso, te asesoran de todo. La venta de mi casa ha sido una maravilla con Enrique y me ha acompañado hasta en la compra de mi otra casa. Se nota que le encanta su trabajo. Recomiendo 100% tanto si vendes como si compras."},
    {"name": "Manuel Escribano Garrido", "role": "5 reseñas", "text": "Una forma honesta y sincera de trabajar por parte de José Enrique. En todo momento atendió mis peticiones, siempre solicito y atento a mis necesidades. Un gran profesional totalmente recomendable."},
    {"name": "Salva Romero", "role": "1 reseña", "text": "De verdad todo un placer haber vendido mi vivienda en esta inmobiliaria, como haber conocido a un equipo de 10. Desde el principio hasta el final han estado al pie del cañón. José Enrique se ha dedicado hasta cuando no le tocaba a él. Siempre agradecido con él y su equipo, en especial también Carmen. Una experiencia de 10. No se lo piensen y compren o vendan con la mejor agencia inmobiliaria, Otro Enfoque para mí la mejor."},
    {"name": "Mar Gallardo", "role": "7 reseñas · 5 fotos", "text": "Nuestra agente José Enrique, un gran profesional cercano y amable. Atento en todo momento a lo que nos hiciera falta."},
    {"name": "Juan Miguel Salvador López", "role": "1 reseña", "text": "Tuve una muy buena experiencia con la inmobiliaria. El personal fue amable y me ayudó en todo momento. Me explicaron bien cada paso y todo se hizo rápido y sin problemas. Muy recomendados."},
    {"name": "Gregorio Gálvez Carrasco", "role": "1 reseña", "text": "Gran profesional José Enrique, educado, serio y resolutivo. Un placer haber tratado con él."},
    {"name": "Juan Herrero", "role": "3 reseñas", "text": "Espectacular trabajo que hicieron por mi vivienda, en menos de un mes consiguieron venderla. Total confianza y claridad para resolver todas las dudas. Súper recomendable, gracias José Enrique."},
    {"name": "Antonio Roque Pradas", "role": "4 reseñas", "text": "El trato con Jose Enrique ha sido increíble. Desde el primer momento mostró una actitud profesional, cercana y con un gran compromiso para colaborar. Es una persona con una visión clara y siempre está dispuesto a encontrar soluciones realmente efectivas."},
    {"name": "Antonio Jose Paredes", "role": "7 reseñas", "text": "Nos lo recomendó un conocido y ha sido todo un acierto. Gran profesional que nos guió y asesoró desde el principio. Todo un acierto."},
    {"name": "Saray Quero Garcia", "role": "3 reseñas", "text": "Aposté por esta inmobiliaria aún sin conocerla y ha sido todo un éxito. Muchas gracias por la dedicación y hacer que sea posible en tan poco tiempo."},
    {"name": "LUIS MARTINEZ RUEDA", "role": "Local Guide · 131 reseñas", "text": "Gran profesionalidad, muy responsables y preocupados por dar la mejor atención a sus clientes. La juventud además es un valor añadido. Altísimamente recomendables."},
    {"name": "Angeles Lopez", "role": "Local Guide · 61 reseñas", "text": "Excelente atención y servicio, nos ayudó Jose Enrique en todo el proceso de forma rápida y profesional."},
]


@app.get("/resenas", response_class=HTMLResponse)
def resenas(request: Request):
    return templates.TemplateResponse(request, "resenas.html", {
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
        "reviews": REVIEWS,
        "canonical": f"{SITE_URL}/resenas",
        "meta_title": "Reseñas de clientes — Otro Enfoque Inmobiliaria",
        "meta_description": "Más de 20 reseñas reales de clientes satisfechos. Descubre por qué Otro Enfoque Inmobiliaria es la mejor opción en Almería.",
    })


@app.get("/contacto", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse(request, "contact.html", {"site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
        "canonical": f"{SITE_URL}/contacto",
        "meta_title": "Contacto — Otro Enfoque Inmobiliaria",
        "meta_description": "Contacta con Otro Enfoque Inmobiliaria en Huércal de Almería. Teléfono, WhatsApp, email y visita a nuestra oficina.",
    })


@app.post("/contacto")
def contact_post(
    request: Request, db: Session = Depends(get_db),
    name: str = Form(...), email: str = Form(...),
    phone: str = Form(""), message: str = Form(...),
):
    if not name.strip() or not email.strip() or not message.strip():
        return templates.TemplateResponse(request, "contact.html", {
            "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
            "error": "Rellena todos los campos obligatorios",
        }, status_code=400)
    contact = ContactMessage(name=name, email=email, phone=phone, message=message)
    db.add(contact)
    db.commit()
    return templates.TemplateResponse(request, "contact.html", {
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
        "success": "Mensaje enviado correctamente. Te responderemos lo antes posible.",
    })


# --- ADMIN ---

@app.get("/admin", response_class=HTMLResponse)
def admin_login(request: Request):
    return templates.TemplateResponse(request, "admin_login.html", {"site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


@app.post("/admin")
def admin_login_post(request: Request, password: str = Form(...)):
    admin_pw = os.getenv("ADMIN_PASSWORD", "admin123")
    if password != admin_pw:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    resp = RedirectResponse("/admin/propiedades", status_code=302)
    resp.set_cookie("admin_token", "authorized", max_age=86400 * 7)
    return resp


def require_admin(request: Request):
    token = request.cookies.get("admin_token")
    if token != "authorized":
        raise HTTPException(status_code=302, detail="No autorizado")


@app.get("/admin/propiedades", response_class=HTMLResponse)
def admin_properties(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    properties = db.query(Property).order_by(desc(Property.created_at)).all()
    return templates.TemplateResponse(request, "admin.html", {"properties": properties, "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


@app.get("/admin/propiedades/nueva", response_class=HTMLResponse)
def admin_new_property(request: Request):
    require_admin(request)
    return templates.TemplateResponse(request, "admin_form.html", {"p": None, "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


@app.post("/admin/propiedades/nueva")
async def admin_create_property(
    request: Request,
    title: str = Form(...), price: float = Form(...),
    operation: str = Form("venta"), property_type: str = Form("piso"),
    bedrooms: int = Form(0), bathrooms: int = Form(0),
    surface: float = Form(0), location: str = Form(""),
    address: str = Form(""), description: str = Form(""),
    features: str = Form(""), latitude: float = Form(None),
    longitude: float = Form(None), status: str = Form("disponible"),
    featured: bool = Form(False), video_url: str = Form(""),
    tour_url: str = Form(""),
    rent: float = Form(None),
    video_file: UploadFile = File(None),
    files_salon: list[UploadFile] = File(default=[]),
    files_cocina: list[UploadFile] = File(default=[]),
    files_dormitorio: list[UploadFile] = File(default=[]),
    files_banyo: list[UploadFile] = File(default=[]),
    files_terraza: list[UploadFile] = File(default=[]),
    files_garaje: list[UploadFile] = File(default=[]),
    files_piscina: list[UploadFile] = File(default=[]),
    files_entrada: list[UploadFile] = File(default=[]),
    files_general: list[UploadFile] = File(default=[]),
    files_otras: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    require_admin(request)
    slug = slugify(title)
    base_slug = slug
    counter = 1
    while db.query(Property).filter(Property.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    prop = Property(
        title=title, slug=slug, price=price, operation=operation,
        property_type=property_type, bedrooms=bedrooms, bathrooms=bathrooms,
        surface=surface, location=location, address=address,
        description=description, features=features,
        latitude=latitude, longitude=longitude,
        status=status, featured=featured, rent=rent, video_url=video_url,
        tour_url=tour_url,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)

    if video_file and video_file.filename:
        content = await video_file.read()
        ext = os.path.splitext(video_file.filename)[1].lower()
        vpath = f"static/properties/{prop.id}_video{ext}"
        with open(vpath, "wb") as out:
            out.write(content)
        prop.video_url = f"/static/properties/{prop.id}_video{ext}"
        db.commit()

    all_file_groups = {
        "salon": files_salon, "cocina": files_cocina,
        "dormitorio": files_dormitorio, "banyo": files_banyo,
        "terraza": files_terraza, "garaje": files_garaje,
        "piscina": files_piscina, "entrada": files_entrada,
        "general": files_general,
        "otras": files_otras,
    }
    saved = []
    for cat_key, file_list in all_file_groups.items():
        for f in file_list:
            if f.filename and f.filename != "":
                content = await f.read()
                src = save_upload(content, f.filename, prop.id, cat_key)
                saved.append({"src": src, "cat": cat_key})
    if saved:
        prop.images = images_to_json(saved)
        db.commit()

    return RedirectResponse(f"/admin/propiedades/{prop.id}/editar", status_code=302)


@app.get("/admin/propiedades/{prop_id}/editar", response_class=HTMLResponse)
def admin_edit_property(prop_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    prop = db.query(Property).filter(Property.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="No encontrada")
    return templates.TemplateResponse(request, "admin_form.html", {"p": prop, "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


@app.post("/admin/propiedades/{prop_id}/editar")
async def admin_update_property(
    prop_id: int, request: Request,
    title: str = Form(...), price: float = Form(...),
    operation: str = Form("venta"), property_type: str = Form("piso"),
    bedrooms: int = Form(0), bathrooms: int = Form(0),
    surface: float = Form(0), location: str = Form(""),
    address: str = Form(""), description: str = Form(""),
    features: str = Form(""), latitude: float = Form(None),
    longitude: float = Form(None), status: str = Form("disponible"),
    featured: bool = Form(False), video_url: str = Form(""),
    tour_url: str = Form(""),
    rent: float = Form(None),
    video_file: UploadFile = File(None),
    files_salon: list[UploadFile] = File(default=[]),
    files_cocina: list[UploadFile] = File(default=[]),
    files_dormitorio: list[UploadFile] = File(default=[]),
    files_banyo: list[UploadFile] = File(default=[]),
    files_terraza: list[UploadFile] = File(default=[]),
    files_garaje: list[UploadFile] = File(default=[]),
    files_piscina: list[UploadFile] = File(default=[]),
    files_entrada: list[UploadFile] = File(default=[]),
    files_general: list[UploadFile] = File(default=[]),
    files_otras: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    require_admin(request)
    prop = db.query(Property).filter(Property.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404)
    if title != prop.title:
        slug = slugify(title)
        base_slug = slug
        counter = 1
        while db.query(Property).filter(Property.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        prop.slug = slug
    prop.title = title
    prop.price = price
    prop.rent = rent
    prop.operation = operation
    prop.property_type = property_type
    prop.bedrooms = bedrooms
    prop.bathrooms = bathrooms
    prop.surface = surface
    prop.location = location
    prop.address = address
    prop.description = description
    prop.features = features
    prop.latitude = latitude
    prop.longitude = longitude
    prop.status = status
    prop.featured = featured
    if video_file and video_file.filename:
        content = await video_file.read()
        ext = os.path.splitext(video_file.filename)[1].lower()
        vpath = f"static/properties/{prop.id}_video{ext}"
        with open(vpath, "wb") as out:
            out.write(content)
        prop.video_url = f"/static/properties/{prop.id}_video{ext}"
    else:
        prop.video_url = video_url
    prop.tour_url = tour_url

    all_file_groups = {
        "salon": files_salon, "cocina": files_cocina,
        "dormitorio": files_dormitorio, "banyo": files_banyo,
        "terraza": files_terraza, "garaje": files_garaje,
        "piscina": files_piscina, "entrada": files_entrada,
        "general": files_general,
        "otras": files_otras,
    }
    saved = []
    for cat_key, file_list in all_file_groups.items():
        for f in file_list:
            if f.filename and f.filename != "":
                content = await f.read()
                src = save_upload(content, f.filename, prop.id, cat_key)
                saved.append({"src": src, "cat": cat_key})
    if saved:
        existing = parse_images(prop.images)
        prop.images = images_to_json(existing + saved)

    prop.updated_at = sqlfunc.now()
    db.commit()
    return RedirectResponse(f"/admin/propiedades/{prop_id}/editar", status_code=302)


@app.post("/admin/propiedades/{prop_id}/upload")
async def admin_upload_images(prop_id: int, request: Request, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    require_admin(request)
    prop = db.query(Property).filter(Property.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404)
    saved = []
    for f in files:
        if f.filename and f.filename != "":
            content = await f.read()
            src = save_upload(content, f.filename, prop_id, "general")
            saved.append({"src": src, "cat": "general"})
    if saved:
        existing = parse_images(prop.images)
        prop.images = images_to_json(existing + saved)
        prop.updated_at = sqlfunc.now()
        db.commit()
    return RedirectResponse(f"/admin/propiedades/{prop_id}/editar", status_code=302)

@app.post("/admin/propiedades/{prop_id}/delete-image")
def admin_delete_image(prop_id: int, request: Request, image: str = Form(...), db: Session = Depends(get_db)):
    require_admin(request)
    prop = db.query(Property).filter(Property.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404)
    images = parse_images(prop.images)
    images = [img for img in images if img["src"] != image]
    prop.images = images_to_json(images)
    if prop.cover_image == image:
        prop.cover_image = ""
    db.commit()
    return RedirectResponse(f"/admin/propiedades/{prop_id}/editar", status_code=302)


@app.post("/admin/propiedades/{prop_id}/set-cover")
def admin_set_cover(prop_id: int, request: Request, image: str = Form(...), db: Session = Depends(get_db)):
    require_admin(request)
    prop = db.query(Property).filter(Property.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404)
    prop.cover_image = image
    db.commit()
    return RedirectResponse(f"/admin/propiedades/{prop_id}/editar", status_code=302)


@app.post("/admin/propiedades/{prop_id}/delete")
def admin_delete_property(prop_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    prop = db.query(Property).filter(Property.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404)
    db.delete(prop)
    db.commit()
    return RedirectResponse("/admin/propiedades", status_code=302)


# --- ADMIN MESSAGES ---

@app.get("/admin/mensajes", response_class=HTMLResponse)
def admin_messages(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    messages = db.query(ContactMessage).order_by(desc(ContactMessage.created_at)).all()
    return templates.TemplateResponse(request, "admin_messages.html", {
        "messages": messages,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


@app.get("/admin/mensajes/{msg_id}", response_class=HTMLResponse)
def admin_message_detail(msg_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    msg = db.query(ContactMessage).filter(ContactMessage.id == msg_id).first()
    if not msg:
        raise HTTPException(status_code=404)
    # Mark as read on first view
    if not msg.is_read:
        msg.is_read = 1
        db.commit()
    return templates.TemplateResponse(request, "admin_message_detail.html", {
        "msg": msg,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


@app.post("/admin/mensajes/{msg_id}/mark-read")
def admin_mark_read(msg_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    msg = db.query(ContactMessage).filter(ContactMessage.id == msg_id).first()
    if msg:
        msg.is_read = 1
        db.commit()
    return RedirectResponse(f"/admin/mensajes/{msg_id}", status_code=302)


@app.post("/admin/mensajes/{msg_id}/delete")
def admin_delete_message(msg_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    msg = db.query(ContactMessage).filter(ContactMessage.id == msg_id).first()
    if msg:
        db.delete(msg)
        db.commit()
    return RedirectResponse("/admin/mensajes", status_code=302)


# --- ADMIN DASHBOARD ---

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    total_props = db.query(Property).count()
    total_views = db.query(sqlfunc.sum(Property.views)).scalar() or 0
    total_messages = db.query(ContactMessage).count()
    total_valuations = db.query(ValuationRequest).count()
    top_props = db.query(Property).order_by(desc(Property.views)).limit(5).all()
    recent_valuations = db.query(ValuationRequest).order_by(desc(ValuationRequest.created_at)).limit(5).all()
    return templates.TemplateResponse(request, "admin_dashboard.html", {
        "total_props": total_props, "total_views": total_views,
        "total_messages": total_messages, "total_valuations": total_valuations,
        "top_props": top_props, "recent_valuations": recent_valuations,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


# --- ADMIN BLOG ---

@app.get("/admin/blog", response_class=HTMLResponse)
def admin_blog_list(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    posts = db.query(BlogPost).order_by(desc(BlogPost.created_at)).all()
    return templates.TemplateResponse(request, "admin_blog.html", {
        "posts": posts,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


@app.get("/admin/blog/nuevo", response_class=HTMLResponse)
def admin_blog_new(request: Request):
    require_admin(request)
    return templates.TemplateResponse(request, "admin_blog_form.html", {
        "post": None,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


@app.post("/admin/blog/nuevo")
def admin_blog_create(
    request: Request, db: Session = Depends(get_db),
    title: str = Form(...), content: str = Form(""),
    excerpt: str = Form(""), image: str = Form(""),
    author: str = Form("Otro Enfoque Inmobiliaria"),
    published: int = Form(1),
):
    require_admin(request)
    slug = slugify(title)
    base_slug = slug
    counter = 1
    while db.query(BlogPost).filter(BlogPost.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    post = BlogPost(title=title, slug=slug, content=content,
        excerpt=excerpt, image=image, author=author, published=published)
    db.add(post)
    db.commit()
    return RedirectResponse("/admin/blog", status_code=302)


@app.get("/admin/blog/{post_id}/editar", response_class=HTMLResponse)
def admin_blog_edit(post_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "admin_blog_form.html", {
        "post": post,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


@app.post("/admin/blog/{post_id}/editar")
def admin_blog_update(
    post_id: int, request: Request, db: Session = Depends(get_db),
    title: str = Form(...), content: str = Form(""),
    excerpt: str = Form(""), image: str = Form(""),
    author: str = Form("Otro Enfoque Inmobiliaria"),
    published: int = Form(1),
):
    require_admin(request)
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404)
    post.title = title
    post.content = content
    post.excerpt = excerpt
    post.image = image
    post.author = author
    post.published = published
    db.commit()
    return RedirectResponse("/admin/blog", status_code=302)


@app.post("/admin/blog/{post_id}/delete")
def admin_blog_delete(post_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if post:
        db.delete(post)
        db.commit()
    return RedirectResponse("/admin/blog", status_code=302)


# --- ADMIN VALUATIONS ---

@app.get("/admin/valoraciones", response_class=HTMLResponse)
def admin_valuations(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    items = db.query(ValuationRequest).order_by(desc(ValuationRequest.created_at)).all()
    for v in items:
        if not v.is_read:
            v.is_read = 1
    db.commit()
    return templates.TemplateResponse(request, "admin_valuations.html", {
        "valuations": items,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


@app.post("/admin/valoraciones/{vid}/delete")
def admin_valuation_delete(vid: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    v = db.query(ValuationRequest).filter(ValuationRequest.id == vid).first()
    if v:
        db.delete(v)
        db.commit()
    return RedirectResponse("/admin/valoraciones", status_code=302)


# --- ADMIN ALERTS ---

@app.get("/admin/alertas", response_class=HTMLResponse)
def admin_alerts(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    alerts = db.query(SearchAlert).order_by(desc(SearchAlert.created_at)).all()
    return templates.TemplateResponse(request, "admin_alerts.html", {
        "alerts": alerts,
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
    })


@app.post("/admin/alertas/{aid}/toggle")
def admin_alert_toggle(aid: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    alert = db.query(SearchAlert).filter(SearchAlert.id == aid).first()
    if alert:
        alert.active = 0 if alert.active else 1
        db.commit()
    return RedirectResponse("/admin/alertas", status_code=302)


@app.get("/api/properties")
def api_properties(db: Session = Depends(get_db)):
    props = db.query(Property).filter(Property.status == "disponible").order_by(desc(Property.created_at)).all()
    return [{
        "id": p.id, "title": p.title, "slug": p.slug, "price": p.price,
        "operation": p.operation, "property_type": p.property_type,
        "bedrooms": p.bedrooms, "bathrooms": p.bathrooms,
        "surface": p.surface, "location": p.location,
        "image": jinja_cover_image(p),
        "featured": p.featured,
    } for p in props]


@app.get("/api/properties/{slug}")
def api_property(slug: str, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.slug == slug).first()
    if not prop:
        raise HTTPException(status_code=404)
    return {
        "id": prop.id, "title": prop.title, "slug": prop.slug,
        "price": prop.price, "description": prop.description,
        "operation": prop.operation, "property_type": prop.property_type,
        "bedrooms": prop.bedrooms, "bathrooms": prop.bathrooms,
        "surface": prop.surface, "location": prop.location,
        "address": prop.address, "latitude": prop.latitude,
        "longitude": prop.longitude,
        "features": [f.strip() for f in prop.features.split(",")] if prop.features else [],
        "images": [img["src"] for img in parse_images(prop.images)],
        "status": prop.status,
    }


# --- SITEMAP ---

@app.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    from fastapi.responses import Response
    props = db.query(Property).filter(Property.status == "disponible").all()
    posts = db.query(BlogPost).filter(BlogPost.published == 1).all()
    urls = [f"<url><loc>{SITE_URL}/</loc></url>",
            f"<url><loc>{SITE_URL}/propiedades</loc></url>",
            f"<url><loc>{SITE_URL}/blog</loc></url>",
            f"<url><loc>{SITE_URL}/valoracion</loc></url>",
            f"<url><loc>{SITE_URL}/resenas</loc></url>",
            f"<url><loc>{SITE_URL}/contacto</loc></url>",
            f"<url><loc>{SITE_URL}/calculadora</loc></url>"]
    for p in props:
        urls.append(f"<url><loc>{SITE_URL}/propiedades/{p.slug}</loc></url>")
    for post in posts:
        urls.append(f"<url><loc>{SITE_URL}/blog/{post.slug}</loc></url>")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{"".join(urls)}
</urlset>"""
    return Response(content=xml, media_type="application/xml")


@app.get("/calculadora", response_class=HTMLResponse)
def calculadora(request: Request):
    return templates.TemplateResponse(request, "calculadora.html", {
        "site_name": SITE_NAME, "whatsapp": WHATSAPP_NUMBER,
        "meta_title": "Calculadora de Hipoteca",
        "meta_description": "Calcula tu cuota hipotecaria mensual y simula tu préstamo para comprar vivienda en Almería.",
        "canonical": f"{SITE_URL}/calculadora",
    })


# --- CHATBOT ---

SYSTEM_PROMPT = (
     "Eres un asistente virtual de Otro Enfoque Inmobiliaria, en Huércal de Almería (Almería). "
     "Dirección: C. Río Júcar 17, 1º-oficina 3, 04230 Huércal de Almería. "
     "Teléfono/WhatsApp: 614 23 40 64 (con prefijo +34 en enlaces wa.me). "
     "Dueño: Jose Enrique Pomedio.\n\n"
     "Respondes SIEMPRE en español, con un tono cercano pero profesional. "
     "No uses markdown ni emojis. "
     "Mantén las respuestas breves y directas (máximo 2-3 párrafos cortos). Ve al grano, sin rodeos.\n\n"
     "IMPORTANTE: Nunca hables en primera persona. No digas 'conmigo', 'contáctame', 'mí', 'yo'. "
     "Habla siempre en nombre de la agencia 'Otro Enfoque Inmobiliaria'. "
     "Usa frases como 'contacta con la agencia', 'puedes contactarnos', 'en Otro Enfoque te ayudamos'.\n\n"
     "Servicios: compraventa, alquiler, valoraciones, gestión hipotecaria, inversión inmobiliaria "
     "en toda la provincia de Almería (Huércal de Almería, Aguadulce, Roquetas de Mar, El Alquián, centro Almería, etc.).\n\n"
      "Si te preguntan algo que no sabes o no está relacionado con el sector inmobiliario en Almería, "
      "responde amablemente que no tienes esa información y sugiéreles contactar por WhatsApp o llamada al 614 23 40 64 "
      "para concertar una cita."
)

FAQ_FALLBACK = [
    (r"\bcomprar\b.*\balquilar\b|\balquilar\b.*\bcomprar\b|\bmejor\b.*\bcomprar\b|\bmejor\b.*\balquilar\b",
     "Hoy en día en Almería, si tienes ahorros y piensas quedarte al menos 5-7 años, comprar suele salir mejor porque el alquiler sube cada año y la hipoteca se queda fija. Si estás solo unos años o no tienes entrada, alquilar es más flexible. ¿Cuál es tu caso? Te ayudo a calcularlo."),
    (r"\bhipoteca\b|\btipo fijo\b|\btipo variable\b|\beur[íi]bor\b|\binter[eé]s\b.*\bhipoteca\b",
     "Sobre hipotecas: necesitas al menos un 20-30% de ahorro del precio. Trabajamos con varias entidades de Almería para conseguirte las mejores condiciones. ¿Quieres que te hagamos un estudio personalizado?"),
     (r"\bvaloraci[oó]n\b|\bvalorar\b.*\bpiso\b|\bvalorar\b.*\bcasa\b|\bcu[aá]nto vale\b",
     "La valoración la hacemos con técnicos certificados en Almería. Te visitamos, analizamos el mercado y te damos un informe detallado sin compromiso. ¿Cuándo te viene bien?"),
    (r"\bgastos\b.*\bcompra\b|\bimpuestos\b.*\bcompra\b|\bitp\b|\biva\b.*\bvivienda\b",
     "Al comprar, suma al precio: ITP/IVA (6-10%), notaría, registro, gestoría y valoración. En total, entre un 10-13% extra."),
    (r"\bgastos\b.*\bventa\b|\bimpuestos\b.*\bventa\b|\bplusval[íi]a\b",
     "Al vender se paga: plusvalía municipal, IRPF por la ganancia patrimonial, notaría y registro. Te ayudamos a calcularlo exacto."),
    (r"\balquiler\b",
     "Para alquiler necesitas: nómina o ingresos regulares, fianza legal (1 mes), y a veces aval bancario o seguro de impago. La fianza se devuelve al final. Tenemos opciones disponibles en Aguadulce y Huércal."),
    (r"\bdeducci[oó]n\b|\bdesgravar\b|\bdeclaraci[oó]n\b.*\bcasa\b|\birpf\b.*\bvivienda\b",
     "Puedes deducirte en IRPF: intereses de hipoteca, alquiler (según tu CCAA), y reformas de eficiencia energética."),
    (r"\beficiencia\b.*\benerg[ée]tica\b|\bcertificado\b.*\benerg[ée]tico\b",
     "El certificado energético es obligatorio para vender o alquilar. Lo hacemos con técnicos homologados en la provincia de Almería en 2-3 días."),
    (r"\binversi[oó]n\b|\brentabilidad\b|\brentable\b|\bcomprar\b.*\binvertir\b",
     "Almería tiene buena rentabilidad, sobre todo Aguadulce, Roquetas y la costa. Te asesoramos sin compromiso para encontrar la mejor inversión."),
    (r"\bvender\b.*\bpiso\b|\bvender\b.*\bcasa\b|\bponer\b.*\bventa\b",
     "Vender con nosotros incluye: valoración realista, fotos profesionales, publicación en portales y acompañamiento en visitas. El tiempo medio de venta en la zona es de 2 a 4 meses."),
]

SALUDOS = r"\bhola\b|\bbuenas\b|\bhello\b|\bhey\b|\bqu[eé] tal\b|\bbuenos d[ií]as\b|\bbuenas tardes\b|\bbuenas noches\b"

if GROQ_API_KEY:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY)

    def groq_chat(message: str) -> str:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        return resp.choices[0].message.content.strip()


@app.post("/api/chat")
def chat(request: Request, message: str = Form(...)):
    msg = message.lower().strip()
    if not msg:
        return JSONResponse({"reply": "¡Hola! Pregúntame lo que necesites sobre compra, venta, alquiler, hipotecas o inversión."})

    if GROQ_API_KEY:
        try:
            reply = groq_chat(message)
            return JSONResponse({"reply": reply})
        except Exception:
            pass

    # Fallback a FAQ si la API falla o no está configurada
    for pattern, reply in FAQ_FALLBACK:
        if re.search(pattern, msg):
            return JSONResponse({"reply": reply})

    if re.search(SALUDOS, msg) and len(msg) < 50:
        return JSONResponse({"reply": "¡Hola! Soy el asistente de Otro Enfoque Inmobiliaria. Pregúntame sobre compra, venta, alquiler, hipotecas, gastos, o cualquier otra duda inmobiliaria."})

    return JSONResponse({"reply": "Perdona, no tengo una respuesta preparada para eso. Pero escríbenos al WhatsApp: https://wa.me/34" + WHATSAPP_NUMBER})

@app.get("/admin/logout")
async def admin_logout():
    r = RedirectResponse(url="/admin", status_code=302)
    r.delete_cookie("admin_token")
    return r

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8022)))
