from __future__ import annotations

from decimal import Decimal
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from app.modules.catalog.models import Product, ProductImage, ProductVariant
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


class Command(BaseCommand):
    help = "Gera massa demo de catálogo tenant-scoped com produtos, variantes e imagens por URL."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-subdomain", default="hubx-demo")
        parser.add_argument("--count", type=int, default=50)
        parser.add_argument("--images-per-product", type=int, default=3)
        parser.add_argument("--reset-seed", action="store_true")
        parser.add_argument("--slug-prefix", default="demo")
        parser.add_argument("--image-host", default="")

    def handle(self, *args, **options):
        tenant_subdomain = str(options["tenant_subdomain"]).strip()
        count = min(max(1, int(options["count"])), len(PRODUCT_BLUEPRINTS))
        images_per_product = min(max(1, int(options["images_per_product"])), 5)
        slug_prefix = slugify(str(options["slug_prefix"] or "demo")) or "demo"
        image_host = str(options.get("image_host") or "").strip().rstrip("/")

        tenant = Tenant.objects.filter(subdomain=tenant_subdomain).first()
        if tenant is None:
            raise CommandError(f"Tenant não encontrado para subdomain={tenant_subdomain}")
        if not image_host:
            image_host = f"http://{tenant.subdomain}.localhost:8002"

        with transaction.atomic():
            if options["reset_seed"]:
                Product.objects.filter(tenant=tenant, slug__startswith=f"{slug_prefix}-").delete()

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
        palettes = (
            ("#f8fafc", "#4f46e5", "#0f172a"),
            ("#eef2ff", "#7c3aed", "#312e81"),
            ("#ecfeff", "#0891b2", "#164e63"),
            ("#fef3c7", "#f59e0b", "#92400e"),
            ("#fce7f3", "#db2777", "#831843"),
        )
        background, accent, foreground = palettes[(index - 1) % len(palettes)]
        safe_tenant = slugify(tenant_subdomain) or "tenant"
        filename = f"{product_slug}-{index}.svg"
        relative_path = Path("demo-catalog") / safe_tenant / filename
        absolute_path = Path(settings.MEDIA_ROOT) / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_text(
            _svg_product_placeholder(
                background=background,
                accent=accent,
                foreground=foreground,
                brand=brand,
                category=category,
                name=name,
                index=index,
            ),
            encoding="utf-8",
        )
        return f"{image_host}{settings.MEDIA_URL}{relative_path.as_posix()}"


def _svg_product_placeholder(
    *,
    background: str,
    accent: str,
    foreground: str,
    brand: str,
    category: str,
    name: str,
    index: int,
) -> str:
    brand_text = escape(brand.upper())
    category_text = escape(category)
    name_text = escape(name)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="900" viewBox="0 0 900 900" role="img" aria-label="{name_text}">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="{background}"/>
      <stop offset="100%" stop-color="#ffffff"/>
    </linearGradient>
  </defs>
  <rect width="900" height="900" fill="url(#bg)"/>
  <circle cx="708" cy="170" r="118" fill="{accent}" opacity="0.16"/>
  <circle cx="170" cy="720" r="150" fill="{accent}" opacity="0.12"/>
  <rect x="96" y="116" width="708" height="668" rx="44" fill="#ffffff" opacity="0.78"/>
  <rect x="142" y="164" width="616" height="390" rx="36" fill="{background}" stroke="{accent}" stroke-width="8"/>
  <path d="M236 456 C306 336 384 396 450 300 C520 196 646 276 692 456 Z" fill="{accent}" opacity="0.88"/>
  <circle cx="314" cy="272" r="48" fill="{foreground}" opacity="0.22"/>
  <text x="450" y="628" text-anchor="middle" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="26" font-weight="700" fill="{accent}">{brand_text}</text>
  <text x="450" y="676" text-anchor="middle" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="42" font-weight="800" fill="{foreground}">{name_text}</text>
  <text x="450" y="728" text-anchor="middle" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="24" font-weight="500" fill="#475569">{category_text} · imagem {index}</text>
</svg>
"""
