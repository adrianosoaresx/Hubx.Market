from __future__ import annotations

import shutil
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from app.modules.catalog.models import Product, ProductImage, ProductVariant, StorefrontDiscoveryEventLog
from app.modules.tenants.models import Tenant


PRODUCT_BLUEPRINTS = [
    ("Tênis Aero Run", "Hubx", "Calçados", "Tênis leve para corrida urbana com amortecimento responsivo.", 299.90),
    ("Tênis Street Flex", "Hubx", "Calçados", "Modelo casual para rotina, caminhada e deslocamentos rápidos.", 249.90),
    ("Tênis Trail Grip", "North Peak", "Calçados", "Solado aderente e cabedal reforçado para trilhas leves.", 389.90),
    ("Sandália Cloud Step", "Orla", "Calçados", "Conforto macio para dias quentes e uso prolongado.", 139.90),
    ("Bota Urban Trek", "North Peak", "Calçados", "Bota versátil com visual urbano e proteção para chuva leve.", 429.90),
    ("Camiseta Dry Fit Core", "Hubx", "Vestuário", "Malha respirável para treino, viagem e rotina.", 89.90),
    ("Camiseta Organic Basic", "Cotton Lab", "Vestuário", "Algodão macio com caimento casual e acabamento limpo.", 79.90),
    ("Polo Commuter", "Cotton Lab", "Vestuário", "Polo estruturada para trabalho casual e pós-treino.", 129.90),
    ("Jaqueta Wind Shield", "North Peak", "Vestuário", "Corta-vento compacto com bolsos seguros.", 299.90),
    ("Moletom Soft Zip", "Cotton Lab", "Vestuário", "Moletom com zíper, toque macio e capuz ajustável.", 219.90),
    ("Calça Jogger Move", "Hubx", "Vestuário", "Jogger elástica para mobilidade e conforto no dia a dia.", 189.90),
    ("Shorts Training Pro", "Hubx", "Vestuário", "Shorts leve com secagem rápida e bolso interno.", 119.90),
    ("Mochila City Pack 20L", "Carry Co", "Acessórios", "Mochila compacta para notebook e itens de rotina.", 239.90),
    ("Mochila Travel Pack 35L", "Carry Co", "Acessórios", "Organização ampla para viagens curtas e trabalho remoto.", 389.90),
    ("Bolsa Tote Canvas", "Orla", "Acessórios", "Tote resistente para mercado, praia e rotina urbana.", 149.90),
    ("Boné Performance Cap", "Hubx", "Acessórios", "Boné leve com ajuste traseiro e proteção solar.", 89.90),
    ("Garrafa Steel 750ml", "Hydra", "Acessórios", "Garrafa térmica de aço inox para treino e escritório.", 129.90),
    ("Óculos Solar Coast", "Orla", "Acessórios", "Óculos com armação leve e lentes polarizadas.", 199.90),
    ("Relógio Fit Pulse", "Pulse", "Eletrônicos", "Monitor de atividades com bateria para vários dias.", 349.90),
    ("Fone Air Mini", "Pulse", "Eletrônicos", "Fone compacto com estojo de carregamento e graves equilibrados.", 249.90),
    ("Speaker Pocket", "Pulse", "Eletrônicos", "Caixa bluetooth portátil para ambientes pequenos.", 179.90),
    ("Carregador GaN Duo", "Volt", "Eletrônicos", "Carregador rápido com duas portas USB-C.", 159.90),
    ("Cabo USB-C Flex", "Volt", "Eletrônicos", "Cabo reforçado para carga rápida e transferência.", 59.90),
    ("Mouse Silent Work", "Deskly", "Eletrônicos", "Mouse silencioso e ergonômico para produtividade.", 119.90),
    ("Teclado Compact Pro", "Deskly", "Eletrônicos", "Teclado compacto para setup híbrido e digitação confortável.", 279.90),
    ("Luminária Focus LED", "Deskly", "Casa", "Luminária de mesa com temperatura ajustável.", 189.90),
    ("Organizador Desk Tray", "Deskly", "Casa", "Bandeja modular para cabos, chaves e acessórios.", 99.90),
    ("Caneca Thermal Mug", "Hydra", "Casa", "Caneca térmica com tampa para café em movimento.", 109.90),
    ("Kit Toalhas Spa", "Orla", "Casa", "Toalhas macias com alta absorção para banho e academia.", 179.90),
    ("Almofada Lumbar Rest", "Deskly", "Casa", "Apoio lombar para cadeira de trabalho ou viagem.", 139.90),
    ("Tapete Yoga Flow", "Zenit", "Fitness", "Tapete antiderrapante para yoga, alongamento e pilates.", 159.90),
    ("Kit Mini Bands", "Zenit", "Fitness", "Faixas elásticas com três níveis de resistência.", 69.90),
    ("Rolo Massage Recovery", "Zenit", "Fitness", "Rolo para liberação miofascial e recuperação muscular.", 119.90),
    ("Luvas Training Grip", "Hubx", "Fitness", "Luvas com palma reforçada para treino funcional.", 89.90),
    ("Corda Speed Jump", "Zenit", "Fitness", "Corda ajustável para treino cardiovascular intenso.", 79.90),
    ("Necessaire Travel Dry", "Carry Co", "Viagem", "Necessaire impermeável para acessórios de higiene.", 99.90),
    ("Cubo Organizador Set", "Carry Co", "Viagem", "Kit de cubos para mala com compressão leve.", 149.90),
    ("Travesseiro Neck Go", "Carry Co", "Viagem", "Travesseiro de pescoço para trajetos longos.", 119.90),
    ("Cadeado TSA Safe", "Carry Co", "Viagem", "Cadeado com segredo numérico para malas.", 69.90),
    ("Tag Bag Finder", "Carry Co", "Viagem", "Identificador de bagagem resistente e colorido.", 39.90),
    ("Sérum Daily Glow", "Aura", "Beleza", "Sérum facial leve para rotina diurna.", 119.90),
    ("Hidratante Body Fresh", "Aura", "Beleza", "Hidratante corporal de rápida absorção.", 79.90),
    ("Protetor Solar Urban FPS50", "Aura", "Beleza", "Protetor solar urbano com toque seco.", 89.90),
    ("Shampoo Balance Care", "Aura", "Beleza", "Shampoo suave para uso frequente.", 59.90),
    ("Condicionador Repair Soft", "Aura", "Beleza", "Condicionador nutritivo para brilho e maciez.", 64.90),
    ("Caderno Planner Weekly", "Paper Co", "Papelaria", "Planner semanal com páginas pontilhadas.", 69.90),
    ("Caneta Gel Smooth Set", "Paper Co", "Papelaria", "Kit de canetas gel para escrita fluida.", 49.90),
    ("Bloco Sticky Notes", "Paper Co", "Papelaria", "Blocos adesivos em cores suaves para organização.", 29.90),
    ("Estojo Tech Pouch", "Carry Co", "Acessórios", "Estojo para cabos, carregadores e pequenos gadgets.", 129.90),
    ("Suporte Notebook Lift", "Deskly", "Eletrônicos", "Suporte dobrável para notebook com ajuste de altura.", 169.90),
]


VARIANT_OPTIONS = {
    "Calçados": ("Preto · 40", "Preto · 41", "Cinza · 42"),
    "Vestuário": ("Preto · M", "Azul · G", "Off-white · P"),
    "Acessórios": ("Grafite · U", "Verde · U", "Areia · U"),
    "Eletrônicos": ("Preto · U", "Branco · U", "Grafite · U"),
    "Casa": ("Natural · U", "Cinza · U", "Azul · U"),
    "Fitness": ("Preto · U", "Roxo · U", "Verde · U"),
    "Viagem": ("Grafite · U", "Azul · U", "Laranja · U"),
    "Beleza": ("Padrão · 100ml", "Padrão · 200ml", "Refil · 200ml"),
    "Papelaria": ("Azul · U", "Verde · U", "Rosa · U"),
}


DEMO_IMAGE_FIXTURE_DIR = Path(settings.BASE_DIR) / "app" / "modules" / "catalog" / "fixtures" / "demo_product_images"
RASTER_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


class Command(BaseCommand):
    help = "Gera massa demo de catálogo tenant-scoped com produtos, variantes e imagens por URL."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-subdomain", default="hubx-demo")
        parser.add_argument("--count", type=int, default=50)
        parser.add_argument("--images-per-product", type=int, default=4)
        parser.add_argument("--reset-seed", action="store_true")
        parser.add_argument("--reset-tenant-catalog", action="store_true")
        parser.add_argument("--clear-discovery-events", action="store_true")
        parser.add_argument("--slug-prefix", default="demo")
        parser.add_argument("--image-host", default="")
        parser.add_argument("--store-name", default="")

    def handle(self, *args, **options):
        tenant_subdomain = str(options["tenant_subdomain"]).strip()
        count = min(max(1, int(options["count"])), len(PRODUCT_BLUEPRINTS))
        images_per_product = min(max(1, int(options["images_per_product"])), 5)
        slug_prefix = slugify(str(options["slug_prefix"] or "demo")) or "demo"
        image_host = str(options.get("image_host") or "").strip().rstrip("/")
        store_name = str(options.get("store_name") or "").strip()

        tenant = Tenant.objects.filter(subdomain=tenant_subdomain).first()
        if tenant is None:
            raise CommandError(f"Tenant não encontrado para subdomain={tenant_subdomain}")
        if not image_host:
            image_host = f"http://{tenant.subdomain}.localhost:8002"

        with transaction.atomic():
            if store_name and tenant.name != store_name:
                tenant.name = store_name
                tenant.save(update_fields=["name", "updated_at"])
            if options["reset_seed"]:
                if options["reset_tenant_catalog"]:
                    Product.objects.filter(tenant=tenant).delete()
                else:
                    Product.objects.filter(tenant=tenant, slug__startswith=f"{slug_prefix}-").delete()
            if options["clear_discovery_events"]:
                StorefrontDiscoveryEventLog.objects.filter(tenant=tenant).delete()

            created_products = 0
            created_variants = 0
            created_images = 0

            for index, blueprint in enumerate(PRODUCT_BLUEPRINTS[:count], start=1):
                name, brand, category, description, base_price = blueprint
                product_slug = f"{slug_prefix}-{slugify(name)}"
                product, product_created = Product.objects.update_or_create(
                    tenant=tenant,
                    slug=product_slug,
                    defaults={
                        "name": name,
                        "description": description,
                        "brand_name": brand,
                        "category_label": category,
                        "status": Product.Status.ACTIVE,
                        "is_active": True,
                        "is_featured": index <= 12 or index % 7 == 0,
                    },
                )
                created_products += int(product_created)

                ProductVariant.objects.filter(product=product).delete()
                ProductImage.objects.filter(product=product).delete()

                stock = self._stock_for(index)
                reserved_stock = min(index % 4, max(stock - 1, 0)) if stock else 0
                variants = VARIANT_OPTIONS.get(category, ("Padrão · U", "Alternativo · U", "Especial · U"))
                for variant_index, variant_label in enumerate(variants, start=1):
                    variant_price = Decimal(str(base_price)) + Decimal(variant_index - 1) * Decimal("10.00")
                    compare_price = variant_price + Decimal("30.00") if index % 3 == 0 else None
                    variant_stock = max(stock - ((variant_index - 1) * 2), 0)
                    ProductVariant.objects.create(
                        product=product,
                        sku=f"{tenant.slug.upper()}-{slug_prefix.upper()}-{index:03d}-{variant_index}",
                        price=variant_price,
                        compare_price=compare_price,
                        stock=variant_stock,
                        reserved_stock=min(reserved_stock, max(variant_stock - 1, 0)) if variant_stock else 0,
                        track_inventory=True,
                        allow_backorder=index % 10 == 0,
                        is_default=variant_index == 1,
                    )
                    created_variants += 1

                for image_index in range(1, images_per_product + 1):
                    image_url = self._create_local_image(
                        tenant_subdomain=tenant.subdomain,
                        image_host=image_host,
                        product_slug=product_slug,
                        brand=brand,
                        category=category,
                        name=name,
                        index=image_index,
                    )
                    ProductImage.objects.create(
                        product=product,
                        image_url=image_url,
                        alt_text=f"{name} · imagem {image_index}",
                        position=image_index,
                        is_primary=image_index == 1,
                    )
                    created_images += 1

        self.stdout.write(
            self.style.SUCCESS(
                "demo_catalog_seeded "
                f"tenant_id={tenant.id} "
                f"tenant_subdomain={tenant.subdomain} "
                f"products={count} "
                f"created_products={created_products} "
                f"variants={created_variants} "
                f"images={created_images} "
                f"image_host={image_host} "
                f"slug_prefix={slug_prefix}"
            )
        )

    @staticmethod
    def _stock_for(index: int) -> int:
        if index % 13 == 0:
            return 0
        if index % 5 == 0:
            return 3
        return 8 + (index % 18)

    @staticmethod
    def _create_local_image(
        *,
        tenant_subdomain: str,
        image_host: str,
        product_slug: str,
        brand: str,
        category: str,
        name: str,
        index: int,
    ) -> str:
        safe_tenant = slugify(tenant_subdomain) or "tenant"
        fixture_source = _fixture_image_source(product_slug=product_slug, category=category, index=index)
        extension = fixture_source.suffix.lower() if fixture_source else ".jpg"
        if extension not in RASTER_EXTENSIONS:
            extension = ".jpg"
        filename = f"{product_slug}-{index}{extension}"
        relative_path = Path("demo-catalog") / safe_tenant / filename
        absolute_path = Path(settings.MEDIA_ROOT) / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        if fixture_source:
            shutil.copyfile(fixture_source, absolute_path)
        else:
            _write_raster_fallback(absolute_path=absolute_path, brand=brand, category=category, name=name, index=index)
        return f"{image_host}{settings.MEDIA_URL}{relative_path.as_posix()}"


def _fixture_image_source(*, product_slug: str, category: str, index: int) -> Path | None:
    candidates: list[Path] = []
    for extension in RASTER_EXTENSIONS:
        candidates.append(DEMO_IMAGE_FIXTURE_DIR / "products" / f"{product_slug}-{index}{extension}")
        candidates.append(DEMO_IMAGE_FIXTURE_DIR / "products" / f"{product_slug}{extension}")
    return next((candidate for candidate in candidates if candidate.exists()), None)


def _write_raster_fallback(
    *,
    absolute_path: Path,
    brand: str,
    category: str,
    name: str,
    index: int,
) -> None:
    try:
        from PIL import Image, ImageDraw
    except Exception as error:  # pragma: no cover - fixtures should normally avoid this path
        raise CommandError("Fixtures raster demo não encontradas e Pillow indisponível para fallback.") from error

    profile = _product_visual_profile(name=name, category=category)
    background, accent, secondary, foreground = _product_palette(category=category, index=index)
    image = Image.new("RGB", (900, 900), background)
    draw = ImageDraw.Draw(image)
    _draw_catalog_backdrop(draw=draw, accent=accent, secondary=secondary, image_index=index)
    _draw_product_subject(draw=draw, product_type=profile, accent=accent, secondary=secondary, foreground=foreground, image_index=index)
    draw.rounded_rectangle((78, 696, 822, 806), radius=28, fill=(255, 255, 255), outline=(226, 232, 240), width=2)
    draw.text((112, 724), brand.upper()[:30], fill=accent)
    draw.text((112, 758), name[:48], fill=foreground)
    draw.text((112, 786), f"{category} · imagem {index}", fill=(71, 85, 105))
    image.save(absolute_path, quality=86)


def _product_visual_profile(*, name: str, category: str) -> str:
    normalized = f"{category} {name}".lower()
    keyword_profiles = (
        (("tênis", "sandália", "bota"), "shoe"),
        (("camiseta", "polo", "jaqueta", "moletom", "calça", "shorts"), "apparel"),
        (("mochila", "bolsa", "necessaire", "cubo", "estojo"), "bag"),
        (("boné",), "cap"),
        (("garrafa", "caneca"), "bottle"),
        (("óculos",), "glasses"),
        (("relógio",), "watch"),
        (("fone",), "earbuds"),
        (("speaker",), "speaker"),
        (("carregador", "cabo"), "charger"),
        (("mouse",), "mouse"),
        (("teclado",), "keyboard"),
        (("luminária",), "lamp"),
        (("organizador",), "tray"),
        (("toalhas",), "towels"),
        (("almofada", "travesseiro"), "pillow"),
        (("tapete",), "mat"),
        (("bands",), "bands"),
        (("rolo",), "roller"),
        (("luvas",), "gloves"),
        (("corda",), "rope"),
        (("cadeado",), "lock"),
        (("tag",), "tag"),
        (("sérum", "hidratante", "protetor", "shampoo", "condicionador"), "beauty"),
        (("caderno", "planner"), "notebook"),
        (("caneta",), "pens"),
        (("sticky", "bloco"), "notes"),
        (("suporte",), "stand"),
    )
    return next((profile for keywords, profile in keyword_profiles if any(keyword in normalized for keyword in keywords)), "box")


def _product_palette(*, category: str, index: int) -> tuple[tuple[int, int, int], ...]:
    palettes = {
        "Calçados": ((244, 247, 251), (31, 41, 55), (100, 116, 139), (15, 23, 42)),
        "Vestuário": ((248, 250, 252), (37, 99, 235), (14, 165, 233), (15, 23, 42)),
        "Acessórios": ((245, 243, 255), (109, 40, 217), (20, 184, 166), (30, 41, 59)),
        "Eletrônicos": ((241, 245, 249), (51, 65, 85), (34, 211, 238), (15, 23, 42)),
        "Casa": ((247, 250, 252), (13, 148, 136), (148, 163, 184), (30, 41, 59)),
        "Fitness": ((240, 253, 250), (5, 150, 105), (249, 115, 22), (20, 83, 45)),
        "Viagem": ((239, 246, 255), (29, 78, 216), (245, 158, 11), (30, 64, 175)),
        "Beleza": ((253, 242, 248), (219, 39, 119), (251, 146, 60), (131, 24, 67)),
        "Papelaria": ((255, 251, 235), (217, 119, 6), (59, 130, 246), (120, 53, 15)),
    }
    base = palettes.get(category, ((248, 250, 252), (79, 70, 229), (20, 184, 166), (15, 23, 42)))
    if index % 2 == 0:
        return base[0], base[2], base[1], base[3]
    return base


def _draw_catalog_backdrop(*, draw, accent: tuple[int, int, int], secondary: tuple[int, int, int], image_index: int) -> None:
    draw.rounded_rectangle((66, 72, 834, 828), radius=48, fill=(255, 255, 255), outline=(226, 232, 240), width=2)
    draw.ellipse((610, 104, 812, 306), fill=(*secondary,))
    draw.ellipse((104, 532, 280, 708), fill=(*accent,))
    draw.rounded_rectangle((152, 588, 748, 626), radius=19, fill=(226, 232, 240))
    if image_index >= 3:
        draw.line((150, 158, 750, 158), fill=(226, 232, 240), width=3)
        draw.line((150, 642, 750, 642), fill=(226, 232, 240), width=3)


def _draw_product_subject(
    *,
    draw,
    product_type: str,
    accent: tuple[int, int, int],
    secondary: tuple[int, int, int],
    foreground: tuple[int, int, int],
    image_index: int,
) -> None:
    outline = foreground
    if product_type == "shoe":
        draw.polygon([(226, 484), (374, 384), (540, 438), (664, 492), (704, 562), (304, 562)], fill=accent, outline=outline)
        draw.rounded_rectangle((296, 544, 716, 610), radius=24, fill=foreground)
        draw.line((384, 430, 486, 462), fill=(255, 255, 255), width=8)
    elif product_type == "apparel":
        draw.polygon([(330, 226), (424, 186), (476, 186), (570, 226), (638, 340), (558, 384), (536, 306), (536, 586), (364, 586), (364, 306), (342, 384), (262, 340)], fill=accent, outline=outline)
        draw.arc((404, 176, 496, 252), 0, 180, fill=(255, 255, 255), width=8)
    elif product_type == "bag":
        draw.rounded_rectangle((286, 260, 614, 604), radius=44, fill=accent, outline=outline, width=5)
        draw.arc((354, 190, 546, 340), 180, 360, fill=foreground, width=18)
        draw.line((346, 396, 554, 396), fill=(255, 255, 255), width=6)
    elif product_type == "cap":
        draw.pieslice((276, 286, 576, 586), 180, 360, fill=accent, outline=outline)
        draw.polygon([(520, 430), (716, 468), (520, 510)], fill=secondary, outline=outline)
    elif product_type == "bottle":
        draw.rounded_rectangle((376, 220, 524, 604), radius=52, fill=accent, outline=outline, width=5)
        draw.rounded_rectangle((404, 168, 496, 238), radius=18, fill=foreground)
        draw.rectangle((394, 382, 506, 444), fill=(255, 255, 255))
    elif product_type == "glasses":
        draw.rounded_rectangle((238, 342, 422, 500), radius=54, fill=accent, outline=outline, width=8)
        draw.rounded_rectangle((478, 342, 662, 500), radius=54, fill=accent, outline=outline, width=8)
        draw.line((422, 416, 478, 416), fill=outline, width=8)
    elif product_type == "watch":
        draw.rounded_rectangle((392, 150, 508, 652), radius=44, fill=secondary)
        draw.rounded_rectangle((320, 284, 580, 520), radius=56, fill=accent, outline=outline, width=7)
        draw.ellipse((392, 356, 508, 472), fill=(255, 255, 255))
    elif product_type in {"earbuds", "charger"}:
        draw.rounded_rectangle((318, 374, 582, 564), radius=46, fill=accent, outline=outline, width=5)
        draw.rounded_rectangle((264, 250, 360, 412), radius=42, fill=secondary, outline=outline, width=5)
        draw.rounded_rectangle((540, 250, 636, 412), radius=42, fill=secondary, outline=outline, width=5)
    elif product_type == "keyboard":
        draw.rounded_rectangle((198, 338, 702, 540), radius=32, fill=accent, outline=outline, width=5)
        for row in range(3):
            for col in range(8):
                draw.rounded_rectangle((234 + col * 56, 374 + row * 42, 274 + col * 56, 402 + row * 42), radius=7, fill=(255, 255, 255))
    elif product_type == "mouse":
        draw.rounded_rectangle((342, 230, 558, 610), radius=96, fill=accent, outline=outline, width=6)
        draw.line((450, 244, 450, 356), fill=(255, 255, 255), width=6)
    elif product_type == "lamp":
        draw.polygon([(380, 236), (562, 236), (622, 392), (318, 392)], fill=accent, outline=outline)
        draw.line((470, 392, 470, 620), fill=outline, width=16)
        draw.rounded_rectangle((340, 608, 600, 650), radius=18, fill=secondary)
    elif product_type in {"mat", "towels"}:
        for offset in (0, 44, 88):
            draw.rounded_rectangle((258 + offset, 286 + offset, 596 + offset, 454 + offset), radius=34, fill=accent if offset == 88 else secondary, outline=outline, width=4)
    elif product_type in {"bands", "rope"}:
        for offset in (0, 84, 168):
            draw.ellipse((234 + offset, 276, 414 + offset, 540), outline=accent if offset != 84 else secondary, width=22)
    elif product_type == "roller":
        draw.rounded_rectangle((246, 338, 654, 514), radius=82, fill=accent, outline=outline, width=5)
        for x in range(304, 620, 58):
            draw.line((x, 350, x - 52, 502), fill=secondary, width=8)
    elif product_type in {"beauty", "pens"}:
        for x, h, color in ((302, 300, accent), (414, 382, secondary), (526, 330, foreground)):
            draw.rounded_rectangle((x, 570 - h, x + 70, 606), radius=24, fill=color, outline=outline, width=4)
            draw.rectangle((x + 16, 548 - h, x + 54, 578 - h), fill=(255, 255, 255))
    elif product_type in {"notebook", "notes"}:
        draw.rounded_rectangle((284, 222, 616, 608), radius=28, fill=accent, outline=outline, width=5)
        for y in range(296, 540, 54):
            draw.line((342, y, 558, y), fill=(255, 255, 255), width=5)
        draw.line((330, 222, 330, 608), fill=secondary, width=14)
    elif product_type == "lock":
        draw.arc((344, 196, 556, 430), 180, 360, fill=outline, width=24)
        draw.rounded_rectangle((306, 386, 594, 606), radius=34, fill=accent, outline=outline, width=5)
    elif product_type in {"pillow", "tray", "stand", "gloves", "tag", "speaker"}:
        draw.rounded_rectangle((282, 278, 618, 574), radius=54, fill=accent, outline=outline, width=5)
        draw.rounded_rectangle((342, 348, 558, 494), radius=28, fill=secondary)
    else:
        draw.rounded_rectangle((284, 286, 616, 596), radius=34, fill=accent, outline=outline, width=5)
    if image_index == 2:
        draw.ellipse((646, 206, 706, 266), fill=(255, 255, 255), outline=secondary, width=8)
    elif image_index == 4:
        draw.rounded_rectangle((214, 184, 336, 236), radius=18, fill=(255, 255, 255), outline=secondary, width=5)
