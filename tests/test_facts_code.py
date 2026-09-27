"""Tests for the routes, services and JS/TS module facts (`kingmadoc explain facts`)."""

from kingmadoc.facts.js_modules import js_dependencies
from kingmadoc.facts.routes import Route, routes
from kingmadoc.facts.services import Service, services

ASPNET_CONTROLLER = """\
[ApiController]
[Route("api/orders")]
[Authorize(Roles = "Admin")]
public class OrdersController : ControllerBase
{
    [HttpGet]
    public IActionResult List() => Ok();

    [HttpPost("{id}/cancel")]
    [EnableRateLimiting("strict")]
    public IActionResult Cancel(int id) => Ok();

    [AllowAnonymous]
    [HttpGet("public")]
    public IActionResult Public() => Ok();
}

[ApiController]
public class ContactController : ControllerBase
{
    [HttpPost("api/contact")]
    public async Task<IActionResult> Send() => Ok();
}
"""

PROGRAM_CS = """\
builder.Services.AddDbContext<ShopDbContext>(options => options.UseSqlite("x"));
builder.Services.AddScoped<IOrderService, OrderService>();
builder.Services.AddSingleton<IClock, SystemClock>();
builder.Services.AddTransient<Mailer>();
builder.Services.AddHttpClient<IPayments, StripePayments>();
app.MapGet("/health", () => "OK");
app.MapPost("/admin/reset", Reset).RequireAuthorization("admin");
"""


def test_aspnet_controller_routes_and_permissions() -> None:
    """Class [Route] + method [Http*]; [Authorize]/[AllowAnonymous]; rate limiting noted.

    Routes are sorted by path, then method.
    """
    found = routes({"Api/Controllers/OrdersController.cs": ASPNET_CONTROLLER})

    assert found == (
        Route("POST", "/api/contact", "ContactController.Send",
              "Api/Controllers/OrdersController.cs", ""),
        Route("GET", "/api/orders", "OrdersController.List",
              "Api/Controllers/OrdersController.cs", "Authorize (Roles = Admin)"),
        Route("GET", "/api/orders/public", "OrdersController.Public",
              "Api/Controllers/OrdersController.cs", "anonymous"),
        Route("POST", "/api/orders/{id}/cancel", "OrdersController.Cancel",
              "Api/Controllers/OrdersController.cs",
              "Authorize (Roles = Admin); rate limit strict"),
    )


def test_minimal_api_routes() -> None:
    """app.MapGet/MapPost, with RequireAuthorization on the same statement."""
    found = routes({"Api/Program.cs": PROGRAM_CS})

    assert [(r.method, r.path, r.access) for r in found] == [
        ("POST", "/admin/reset", "RequireAuthorization (admin)"),
        ("GET", "/health", ""),
    ]


def test_nextjs_app_and_pages_routes() -> None:
    """app/**/page.tsx are pages; app/**/route.ts export HTTP methods; pages/ and pages/api/."""
    found = routes({
        "frontend/app/page.tsx": "export default function Home() {}",
        "frontend/app/projects/[slug]/page.tsx": "export default function P() {}",
        "frontend/app/api/contact/route.ts": "export async function POST(req) {}\n"
                                             "export function GET() {}",
        "web/pages/about.tsx": "export default function About() {}",
        "web/pages/api/ping.ts": "export default function handler() {}",
        "frontend/components/footer.tsx": "export default function Footer() {}",
    })

    assert [(r.method, r.path, r.handler) for r in found] == [
        ("PAGE", "/", "frontend/app/page.tsx"),
        ("PAGE", "/about", "web/pages/about.tsx"),
        ("GET", "/api/contact", "frontend/app/api/contact/route.ts"),
        ("POST", "/api/contact", "frontend/app/api/contact/route.ts"),
        ("ANY", "/api/ping", "web/pages/api/ping.ts"),
        ("PAGE", "/projects/[slug]", "frontend/app/projects/[slug]/page.tsx"),
    ]


def test_python_web_routes() -> None:
    """Django urls.py (with login_required views), FastAPI and Flask decorators."""
    found = routes({
        "shop/urls.py": 'urlpatterns = [\n    path("orders/", views.create_order),\n'
                        '    path("orders/<int:order_id>/pay/", views.pay_order),\n]\n',
        "shop/views.py": "@login_required\n@require_POST\ndef create_order(request):\n    pass\n\n"
                         "def pay_order(request, order_id):\n    pass\n",
        "api/main.py": '@app.get("/items/{id}")\ndef read(id): ...\n'
                       '@router.post("/items", dependencies=[Depends(auth)])\ndef make(): ...\n',
        "web/app.py": '@app.route("/login", methods=["GET", "POST"])\ndef login(): ...\n',
    })

    assert [(r.method, r.path, r.handler, r.access) for r in found] == [
        ("POST", "/items", "make", "Depends(auth)"),
        ("GET", "/items/{id}", "read", ""),
        ("GET, POST", "/login", "login", ""),
        ("POST", "/orders/", "views.create_order", "login_required"),
        ("ANY", "/orders/<int:order_id>/pay/", "views.pay_order", ""),
    ]


def test_express_routes() -> None:
    """app.get / router.post with the middleware names before the handler."""
    found = routes({"server/index.js": (
        "app.get('/health', (req, res) => res.send('ok'));\n"
        "router.post('/orders', requireAuth, createOrder);\n"
    )})

    assert [(r.method, r.path, r.access) for r in found] == [
        ("GET", "/health", ""),
        ("POST", "/orders", "requireAuth"),
    ]


def test_dotnet_services() -> None:
    """DI registrations: lifetime, contract and implementation."""
    found = services({"Api/Program.cs": PROGRAM_CS})

    assert found == (
        Service("scoped", "ShopDbContext", "ShopDbContext", "Api/Program.cs"),
        Service("scoped", "IOrderService", "OrderService", "Api/Program.cs"),
        Service("singleton", "IClock", "SystemClock", "Api/Program.cs"),
        Service("transient", "Mailer", "Mailer", "Api/Program.cs"),
        Service("http client", "IPayments", "StripePayments", "Api/Program.cs"),
    )


def test_js_dependencies_with_aliases_and_index_files() -> None:
    """Relative and @/ imports resolve to project files; packages are left out."""
    sources = {
        "frontend/tsconfig.json": '{"compilerOptions": {"paths": {"@/*": ["./*"]}}}',
        "frontend/app/page.tsx": 'import Footer from "@/components/footer";\n'
                                 'import { Hero } from "../components/home";\n'
                                 'import React from "react";\n',
        "frontend/components/footer.tsx": 'import { links } from "./profile-links";\n',
        "frontend/components/profile-links.ts": "export const links = [];\n",
        "frontend/components/home/index.ts": 'export * from "./hero";\n',
        "frontend/components/home/hero.tsx": "export function Hero() {}\n",
    }

    edges = js_dependencies(sources)

    assert edges == (
        ("frontend/app/page", "frontend/components/footer"),
        ("frontend/app/page", "frontend/components/home/index"),
        ("frontend/components/footer", "frontend/components/profile-links"),
        ("frontend/components/home/index", "frontend/components/home/hero"),
    )


def test_big_js_graphs_are_merged_into_folders() -> None:
    """More than max_nodes modules: edges between folders instead."""
    sources = {f"src/a/m{i}.ts": f'import "../b/n{i}";\n' for i in range(20)}
    sources.update({f"src/b/n{i}.ts": "" for i in range(20)})

    assert js_dependencies(sources, max_nodes=10) == (("src/a", "src/b"),)


def test_tsconfig_globs_and_comments_do_not_break_the_aliases() -> None:
    """"**/*.ts" in include is a string, not a comment; real comments are ignored."""
    sources = {
        "web/tsconfig.json": (
            '{\n  // the Next.js defaults\n  "compilerOptions": {"paths": {"@/*": ["./*"]}},\n'
            '  /* files */ "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],\n}\n'
        ),
        "web/app/page.tsx": 'import Footer from "@/components/footer";\n',
        "web/components/footer.tsx": "export default function Footer() {}\n",
    }

    assert js_dependencies(sources) == (("web/app/page", "web/components/footer"),)
