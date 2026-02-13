#!/usr/bin/env python3
"""
Generate diagram images from ASCII art for Confluence documentation.
Creates professional SVG and PNG versions of all architecture diagrams.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Create output directory
DIAGRAMS_DIR = Path(__file__).parent.parent / "docs" / "diagrams"
DIAGRAMS_DIR.mkdir(exist_ok=True)

# Font settings (using default since custom fonts may not be available)
try:
    font_small = ImageFont.truetype("arial.ttf", 14)
    font_medium = ImageFont.truetype("arial.ttf", 16)
    font_large = ImageFont.truetype("arial.ttf", 18)
except:
    font_small = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_large = ImageFont.load_default()


def create_architecture_overview():
    """Create the layered architecture diagram."""
    width, height = 1000, 800
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    # Colors
    color_box = "#E8F4F8"
    color_border = "#0066CC"
    color_text = "#000000"
    color_arrow = "#0066CC"

    # Layer boxes
    layers = [
        ("Client Request", 350, 50),
        ("Middleware Layer", 300, 150),
        ("API Layer\napp/api/", 300, 250),
        ("Dependency Layer\napp/api/*/deps/", 300, 350),
        ("Service Layer\napp/services/", 250, 450),
        ("Repository Layer\napp/repos/", 250, 550),
        ("Database\n(PostgreSQL)", 250, 650),
    ]

    for i, (label, width_val, y) in enumerate(layers):
        x = 150
        h = 70
        # Draw box
        draw.rectangle([x, y, x + 700, y + h], fill=color_box, outline=color_border, width=2)
        # Draw text
        draw.text((x + 20, y + 15), label, fill=color_text, font=font_medium)

        # Draw arrow to next layer
        if i < len(layers) - 1:
            draw.line([(500, y + h), (500, layers[i + 1][2])], fill=color_arrow, width=3)
            draw.polygon(
                [
                    (500, layers[i + 1][2] - 10),
                    (495, layers[i + 1][2] - 20),
                    (505, layers[i + 1][2] - 20),
                ],
                fill=color_arrow,
            )

    # Side annotations
    annotations = [
        ("Security headers, CSRF, logging, rate limits", 850, 190),
        ("Routes, auth, status codes", 850, 290),
        ("Session mgmt, repo creation,\nexception translation", 850, 390),
        ("Business logic, domain rules,\nrepo calls", 850, 490),
        ("Data access, CRUD,\nauto_commit", 850, 590),
        ("Tables, ORM mapping", 850, 690),
    ]

    for text, x, y in annotations:
        draw.text((x, y), text, fill="#666666", font=font_small)

    img.save(DIAGRAMS_DIR / "01_architecture_overview.png")
    print("✓ Generated: 01_architecture_overview.png")


def create_import_direction():
    """Create the import direction dependency diagram."""
    width, height = 1200, 900
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    color_api = "#FFE6E6"
    color_service = "#E6F3FF"
    color_model = "#E6FFE6"
    color_core = "#F5F5F5"
    color_border = "#333333"
    color_arrow = "#0066CC"

    # Layers with positions
    layers = {
        "API": {"x": 100, "y": 50, "w": 200, "h": 80, "color": color_api},
        "Deps": {"x": 100, "y": 200, "w": 200, "h": 80, "color": color_api},
        "Service": {"x": 50, "y": 350, "w": 150, "h": 80, "color": color_service},
        "Repository": {"x": 250, "y": 350, "w": 150, "h": 80, "color": color_service},
        "Schemas": {"x": 50, "y": 550, "w": 150, "h": 80, "color": color_model},
        "Models": {"x": 250, "y": 550, "w": 150, "h": 80, "color": color_model},
        "Core": {"x": 450, "y": 550, "w": 150, "h": 80, "color": color_core},
    }

    # Draw boxes
    for name, info in layers.items():
        x, y, w, h, color = info["x"], info["y"], info["w"], info["h"], info["color"]
        draw.rectangle([x, y, x + w, y + h], fill=color, outline=color_border, width=2)
        draw.text((x + 10, y + 30), name, fill=color_border, font=font_medium)

    # Draw arrows (import direction - top to bottom)
    arrows = [
        ((200, 130), (200, 200)),  # API to Deps
        ((175, 280), (125, 350)),  # Deps to Service
        ((225, 280), (275, 350)),  # Deps to Repository
        ((125, 430), (125, 550)),  # Service to Schemas
        ((275, 430), (325, 550)),  # Repository to Models
        ((200, 280), (525, 550)),  # Deps to Core
    ]

    for start, end in arrows:
        draw.line([start, end], fill=color_arrow, width=3)
        # Arrowhead
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        import math

        angle = math.atan2(dy, dx)
        arrowhead_size = 10
        p1 = (
            end[0] - arrowhead_size * math.cos(angle - math.pi / 6),
            end[1] - arrowhead_size * math.sin(angle - math.pi / 6),
        )
        p2 = (
            end[0] - arrowhead_size * math.cos(angle + math.pi / 6),
            end[1] - arrowhead_size * math.sin(angle + math.pi / 6),
        )
        draw.polygon([end, p1, p2], fill=color_arrow)

    # Add rule text
    draw.text(
        (500, 100),
        "Golden Rule: Lower layers MUST NOT import from higher layers",
        fill="#CC0000",
        font=font_medium,
    )

    img.save(DIAGRAMS_DIR / "02_import_direction.png")
    print("✓ Generated: 02_import_direction.png")


def create_test_pyramid():
    """Create the test pyramid diagram."""
    width, height = 900, 700
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    # Triangle pyramid
    pyramid_points = [
        (450, 100),  # Top
        (150, 650),  # Bottom left
        (750, 650),  # Bottom right
    ]

    # Draw pyramid sections
    draw.polygon([(450, 100), (300, 350), (600, 350)], fill="#FFE6E6", outline="#CC0000", width=2)
    draw.polygon([(300, 350), (250, 500), (650, 500)], fill="#FFE8B6", outline="#FF9900", width=2)
    draw.polygon([(250, 500), (150, 650), (750, 650)], fill="#B6FFB6", outline="#00CC00", width=2)

    # Labels
    draw.text((380, 200), "E2E Tests", fill="#CC0000", font=font_large)
    draw.text((320, 400), "Integration Tests", fill="#FF9900", font=font_medium)
    draw.text((280, 570), "Unit Tests (Mocked)", fill="#00CC00", font=font_medium)

    # Descriptions
    draw.text((450, 140), "Full request lifecycle", fill="#CC0000", font=font_small)
    draw.text((320, 430), "Real DB session", fill="#FF9900", font=font_small)
    draw.text((280, 600), "Fast, many, focused", fill="#00CC00", font=font_small)

    img.save(DIAGRAMS_DIR / "03_test_pyramid.png")
    print("✓ Generated: 03_test_pyramid.png")


def create_request_lifecycle():
    """Create the request lifecycle flow diagram."""
    width, height = 1200, 400
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    color_box = "#E8F4F8"
    color_border = "#0066CC"
    color_text = "#000000"

    # Boxes in sequence
    boxes = [
        ("Client", 50),
        ("API", 200),
        ("Deps", 350),
        ("Service", 500),
        ("Repository", 650),
        ("Database", 800),
    ]

    box_width = 100
    box_height = 80
    y = 150

    for label, x in boxes:
        # Draw box
        draw.rectangle(
            [x, y, x + box_width, y + box_height], fill=color_box, outline=color_border, width=2
        )
        draw.text((x + 15, y + 30), label, fill=color_text, font=font_medium)

        # Draw arrow to next
        if label != "Database":
            next_x = [b[1] for b in boxes if b[0] != label]
            if next_x:
                draw.line(
                    [(x + box_width, y + 40), (min(next_x), y + 40)], fill=color_border, width=2
                )
                draw.polygon(
                    [(min(next_x), y + 40), (min(next_x) - 10, y + 35), (min(next_x) - 10, y + 45)],
                    fill=color_border,
                )

    # Response direction below
    draw.text(
        (600, 300),
        "Response: DB → Repo (Model) → Service (Schema) → Deps (Schema) → API (JSON) → Client",
        fill="#666666",
        font=font_small,
    )

    img.save(DIAGRAMS_DIR / "04_request_lifecycle.png")
    print("✓ Generated: 04_request_lifecycle.png")


def create_error_flow():
    """Create the error propagation flow diagram."""
    width, height = 1100, 450
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    color_error = "#FFB3B3"
    color_border = "#CC0000"

    # Flow boxes
    boxes = [
        ("SQLAlchemy\nException", 50),
        ("Service:\nCatch →\nRaise Domain", 250),
        ("Deps:\nCatch Domain →\nRaise HTTP", 500),
        ("API:\nFastAPI auto-\nhandles", 750),
    ]

    y = 150
    for label, x in boxes:
        draw.rectangle([x, y, x + 150, y + 120], fill=color_error, outline=color_border, width=2)
        draw.text((x + 10, y + 30), label, fill=color_border, font=font_small)

        if label != boxes[-1][0]:
            draw.line([(x + 150, y + 60), (x + 200, y + 60)], fill=color_border, width=3)
            draw.polygon(
                [(x + 200, y + 60), (x + 190, y + 55), (x + 190, y + 65)], fill=color_border
            )

    # Add note
    draw.text(
        (400, 350),
        "Error handling flows UP through layers: DB exceptions → Domain exceptions → HTTP exceptions",
        fill="#CC0000",
        font=font_medium,
    )

    img.save(DIAGRAMS_DIR / "05_error_flow.png")
    print("✓ Generated: 05_error_flow.png")


def create_decision_tree():
    """Create a simplified decision tree for layer placement."""
    width, height = 1000, 700
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    color_box = "#F0F0F0"
    color_decision = "#FFE8B6"
    color_leaf = "#B6FFB6"
    color_border = "#333333"

    # Root
    draw.rectangle([350, 20, 650, 80], fill=color_decision, outline=color_border, width=2)
    draw.text((380, 45), "New Code", fill=color_border, font=font_medium)

    # Level 1
    draw.rectangle([100, 150, 350, 210], fill=color_decision, outline=color_border, width=2)
    draw.text((120, 170), "HTTP-related?", fill=color_border, font=font_small)

    draw.rectangle([450, 150, 700, 210], fill=color_decision, outline=color_border, width=2)
    draw.text((480, 170), "Business logic?", fill=color_border, font=font_small)

    # Connections
    draw.line([(500, 80), (225, 150)], fill=color_border, width=2)
    draw.line([(500, 80), (575, 150)], fill=color_border, width=2)

    # Leaves
    draw.rectangle([50, 320, 200, 380], fill=color_leaf, outline=color_border, width=2)
    draw.text((70, 340), "→ API Layer", fill=color_border, font=font_small)

    draw.rectangle([250, 320, 400, 380], fill=color_leaf, outline=color_border, width=2)
    draw.text((270, 340), "→ Service Layer", fill=color_border, font=font_small)

    draw.rectangle([450, 320, 600, 380], fill=color_leaf, outline=color_border, width=2)
    draw.text((470, 340), "→ Service Layer", fill=color_border, font=font_small)

    draw.rectangle([650, 320, 800, 380], fill=color_leaf, outline=color_border, width=2)
    draw.text((670, 340), "→ Repository", fill=color_border, font=font_small)

    draw.text(
        (300, 500),
        "Use the full decision tree in the architecture guide for detailed flow",
        fill="#666666",
        font=font_medium,
    )

    img.save(DIAGRAMS_DIR / "06_decision_tree_simplified.png")
    print("✓ Generated: 06_decision_tree_simplified.png")


def create_scalability_indicator():
    """Create a scalability traffic light indicator."""
    width, height = 1000, 300
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    # Traffic lights
    lights = [
        ("Green: 1-8 devs\n10-80 endpoints\nStay Here", 100, "#00CC00"),
        ("Yellow: 8-15 devs\n80-150 endpoints\nStart Refactoring", 400, "#FFCC00"),
        ("Red: 15+ devs\n150+ endpoints\nNew Architecture", 700, "#CC0000"),
    ]

    for label, x, color in lights:
        # Draw circle
        draw.ellipse([x - 40, 50, x + 40, 130], fill=color, outline="#333333", width=2)
        # Draw label
        draw.text((x - 70, 160), label, fill="#333333", font=font_small)

    img.save(DIAGRAMS_DIR / "07_scalability_lights.png")
    print("✓ Generated: 07_scalability_lights.png")


def main():
    """Generate all diagrams."""
    print(f"Generating diagrams in: {DIAGRAMS_DIR}\n")

    create_architecture_overview()
    create_import_direction()
    create_test_pyramid()
    create_request_lifecycle()
    create_error_flow()
    create_decision_tree()
    create_scalability_indicator()

    print(f"\n✓ All diagrams generated successfully!")
    print(f"📁 Location: {DIAGRAMS_DIR}")
    print("\nNext steps:")
    print("1. Upload these images to Confluence")
    print("2. Update the markdown to reference the image files")
    print("3. Use ![alt text](diagrams/filename.png) syntax")


if __name__ == "__main__":
    main()
