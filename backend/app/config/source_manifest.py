CONFLUENCE_PAGE_ACCESS = {
    # TECH - 7 pages
    "System Overview & High-Level Architecture": ("TECH", "L1", "BC-TECH-L1"),
    "Frontend Architecture & Component System": ("TECH", "L1", "BC-TECH-L1"),
    "Backend Architecture & Data Layer": ("TECH", "L1", "BC-TECH-L1"),
    "Deployment, Infrastructure & Developer Guide": ("TECH", "L1", "BC-TECH-L1"),
    "Admin Dashboard - Architecture & Features": ("TECH", "L2", "BC-TECH-L2"),
    "Authentication & Security Architecture": ("TECH", "L2", "BC-TECH-L2"),
    "Payment Integration with Stripe": ("TECH", "L3", "BC-TECH-L3"),

    # HR - 7 pages
    "Leave Management": ("HR", "L1", "BC-HR-L1"),
    "Workforce Overview": ("HR", "L1", "BC-HR-L1"),
    "HR Policy & Document Registry": ("HR", "L1", "BC-HR-L1"),
    "Key HR Actions & Recommendations": ("HR", "L1", "BC-HR-L1"),
    "Recruiting & Open Requisitions": ("HR", "L2", "BC-HR-L2"),
    "Performance Reviews": ("HR", "L2", "BC-HR-L2"),
    "Compensation & Pay Bands": ("HR", "L3", "BC-HR-L3"),

    # FINANCE - 6 pages
    "Finance Team Overview": ("FINANCE", "L1", "BC-FINANCE-L1"),
    "Headcount Planning & Requisitions": ("FINANCE", "L1", "BC-FINANCE-L1"),
    "Finance Actions & Recommendations": ("FINANCE", "L1", "BC-FINANCE-L1"),
    "Company-Wide Payroll Analysis": ("FINANCE", "L1", "BC-FINANCE-L1"),
    "Payroll Banking & Disbursement": ("FINANCE", "L2", "BC-FINANCE-L2"),
    "Finance Team: Compensation & Performance": ("FINANCE", "L3", "BC-FINANCE-L3"),

    # OPERATIONS - 6 pages
    "Operations Team Overview": ("OPERATIONS", "L1", "BC-OPERATIONS-L1"),
    "Order Fulfillment Operations": ("OPERATIONS", "L1", "BC-OPERATIONS-L1"),
    "Product Catalog & Inventory Operations": ("OPERATIONS", "L1", "BC-OPERATIONS-L1"),
    "Vendor Management & Operational KPIs": ("OPERATIONS", "L1", "BC-OPERATIONS-L1"),
    "Active Operational Initiatives": ("OPERATIONS", "L2", "BC-OPERATIONS-L2"),
    "Team Compensation, Leave & Recommended Actions": ("OPERATIONS", "L3", "BC-OPERATIONS-L3"),
}


GITHUB_EXCLUDED_DIRS = {
    ".git", "node_modules", "dist", "build", ".next",
    "coverage", ".turbo", ".vercel",
}

GITHUB_EXCLUDED_FILENAMES = {
    ".DS_Store", "favicon.ico", "package-lock.json",
    "yarn.lock", "pnpm-lock.yaml", ".gitignore",
    "components.json", "tsconfig.json", "eslint.config.mjs",
    "next.config.ts", "postcss.config.mjs", "tailwind.config.ts",
    "package.json",
}

GITHUB_EXCLUDED_EXTENSIONS = {
    ".svg", ".ico", ".png", ".jpg", ".jpeg", ".gif",
    ".webp", ".mp4", ".mov", ".zip", ".pdf",
    ".ttf", ".woff", ".woff2",
}

GITHUB_ALLOWED_EXTENSIONS = {
    ".md", ".txt", ".ts", ".tsx", ".js", ".jsx", ".css", ".scss",
}


GITHUB_EXPLICIT_ACCESS = {
    "borcella_admin/middleware.ts": ("TECH", "L3", "BC-GITHUB-TECH-L3"),
    "borcella_admin/app/(auth)/layout.tsx": ("TECH", "L3", "BC-GITHUB-TECH-L3"),

    "borcella_admin/app/(dashboard)/layout.tsx": ("TECH", "L2", "BC-GITHUB-TECH-L2"),
    "borcella_admin/app/(dashboard)/page.tsx": ("TECH", "L2", "BC-GITHUB-TECH-L2"),
    "borcella_admin/components/custom ui/ImageUpload.tsx": ("TECH", "L2", "BC-GITHUB-TECH-L2"),
    "borcella_admin/components/collections/CollectionForm.tsx": ("TECH", "L2", "BC-GITHUB-TECH-L2"),
    "borcella_admin/lib/utils.ts": ("TECH", "L2", "BC-GITHUB-TECH-L2"),
    "borcella_admin/lib/constants.tsx": ("TECH", "L2", "BC-GITHUB-TECH-L2"),
}


def classify_github_path(path: str):
    normalized = path.strip()

    if normalized in GITHUB_EXPLICIT_ACCESS:
        return GITHUB_EXPLICIT_ACCESS[normalized]

    p = normalized.lower()

    if not p.startswith("borcella_admin/"):
        return None

    filename = p.split("/")[-1]

    if filename in GITHUB_EXCLUDED_FILENAMES:
        return None

    if any(part in GITHUB_EXCLUDED_DIRS for part in p.split("/")):
        return None

    if any(p.endswith(ext) for ext in GITHUB_EXCLUDED_EXTENSIONS):
        return None

    if not any(p.endswith(ext) for ext in GITHUB_ALLOWED_EXTENSIONS):
        return None

    if "/(auth)/" in p or "middleware" in p:
        return ("TECH", "L3", "BC-GITHUB-TECH-L3")

    if "/(dashboard)/" in p or "/collections/" in p or "/custom ui/" in p or "/lib/" in p:
        return ("TECH", "L2", "BC-GITHUB-TECH-L2")

    return ("TECH", "L1", "BC-GITHUB-TECH-L1")


def classify_drive_file(name: str, parent_path: str = ""):
    combined = f"{parent_path}/{name}".lower()

    if "/l3/" in combined:
        return ("HR", "L3", "BC-HR-GDRIVE-L3")

    if "/l2/" in combined:
        return ("HR", "L2", "BC-HR-GDRIVE-L2")

    return ("HR", "L1", "BC-HR-GDRIVE-L1")