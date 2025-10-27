#!/usr/bin/env python3
"""
Page Object Model Generator

Generates Page Object Model classes from HTML pages or existing test files,
supporting Playwright, Cypress, and Selenium frameworks.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse


VERSION = "1.0.0"


@dataclass
class PageElement:
    """Represents an interactive element on a page."""
    name: str
    element_type: str  # button, input, link, etc.
    selector: str
    selector_type: str  # css, xpath, data-testid, etc.
    description: Optional[str] = None


@dataclass
class PageAction:
    """Represents an action that can be performed on a page."""
    name: str
    description: str
    elements_used: List[str] = field(default_factory=list)
    returns_new_page: Optional[str] = None


@dataclass
class PageModel:
    """Complete page object model."""
    name: str
    url: str
    description: str
    elements: List[PageElement] = field(default_factory=list)
    actions: List[PageAction] = field(default_factory=list)
    components: List[str] = field(default_factory=list)


class PageObjectGenerator:
    """Generate Page Object Model classes."""

    # Common interactive elements
    INTERACTIVE_ELEMENTS = {
        'button', 'a', 'input', 'select', 'textarea',
        'form', '[role="button"]', '[role="link"]'
    }

    # Common test id attributes
    TEST_ID_ATTRS = ['data-testid', 'data-test', 'data-cy', 'data-pw']

    def __init__(self, config: argparse.Namespace):
        self.config = config
        self.framework = config.framework
        self.output_dir = Path(config.output_dir)
        self.language = config.language
        self.verbose = config.verbose

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """Log message to stderr."""
        if self.config.json_output:
            return

        colors = {
            "INFO": "\033[0;34m",
            "SUCCESS": "\033[0;32m",
            "WARNING": "\033[1;33m",
            "ERROR": "\033[0;31m",
        }
        reset = "\033[0m"
        color = colors.get(level, "")
        print(f"{color}[{level}]{reset} {message}", file=sys.stderr)

    def generate_from_url(self, url: str) -> PageModel:
        """Generate page object from URL."""
        self.log(f"Generating page object from URL: {url}")

        # Parse URL to get page name
        parsed = urlparse(url)
        page_name = self._url_to_page_name(parsed.path)

        # Create basic page model
        model = PageModel(
            name=page_name,
            url=url,
            description=f"Page object for {url}"
        )

        # Note: In a real implementation, this would fetch and parse the HTML
        # For now, we generate a template
        self._add_common_elements(model)

        return model

    def generate_from_html(self, html_file: Path) -> PageModel:
        """Generate page object from HTML file."""
        self.log(f"Generating page object from HTML: {html_file}")

        if not html_file.exists():
            raise FileNotFoundError(f"HTML file not found: {html_file}")

        page_name = self._filename_to_page_name(html_file.stem)

        # Read HTML content
        html_content = html_file.read_text()

        # Create page model
        model = PageModel(
            name=page_name,
            url=f"/{html_file.stem}",
            description=f"Page object for {html_file.name}"
        )

        # Extract elements
        self._extract_elements_from_html(html_content, model)

        # Infer common actions
        self._infer_actions(model)

        return model

    def generate_from_test(self, test_file: Path) -> List[PageModel]:
        """Generate page objects from existing test file."""
        self.log(f"Generating page objects from test: {test_file}")

        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")

        test_content = test_file.read_text()

        # Extract page interactions
        pages = self._extract_pages_from_test(test_content)

        return pages

    def _url_to_page_name(self, path: str) -> str:
        """Convert URL path to page class name."""
        if not path or path == "/":
            return "HomePage"

        # Remove leading/trailing slashes
        path = path.strip("/")

        # Convert to PascalCase
        parts = [p.capitalize() for p in re.split(r'[-_/]', path)]
        return "".join(parts) + "Page"

    def _filename_to_page_name(self, filename: str) -> str:
        """Convert filename to page class name."""
        # Remove extensions and convert to PascalCase
        name = filename.replace("-", "_").replace(".", "_")
        parts = [p.capitalize() for p in name.split("_")]
        return "".join(parts) + "Page"

    def _add_common_elements(self, model: PageModel):
        """Add common page elements."""
        # Navigation
        model.elements.append(PageElement(
            name="logo",
            element_type="link",
            selector="a.logo",
            selector_type="css",
            description="Site logo / home link"
        ))

        # Search
        if "search" in model.url.lower():
            model.elements.append(PageElement(
                name="searchInput",
                element_type="input",
                selector="input[type='search']",
                selector_type="css",
                description="Search input field"
            ))
            model.elements.append(PageElement(
                name="searchButton",
                element_type="button",
                selector="button[type='submit']",
                selector_type="css",
                description="Search submit button"
            ))

        # Login elements
        if "login" in model.url.lower():
            model.elements.extend([
                PageElement(
                    name="usernameInput",
                    element_type="input",
                    selector="input[name='username']",
                    selector_type="css",
                    description="Username input"
                ),
                PageElement(
                    name="passwordInput",
                    element_type="input",
                    selector="input[type='password']",
                    selector_type="css",
                    description="Password input"
                ),
                PageElement(
                    name="loginButton",
                    element_type="button",
                    selector="button[type='submit']",
                    selector_type="css",
                    description="Login submit button"
                ),
            ])

            # Add login action
            model.actions.append(PageAction(
                name="login",
                description="Authenticate user with credentials",
                elements_used=["usernameInput", "passwordInput", "loginButton"],
                returns_new_page="DashboardPage"
            ))

    def _extract_elements_from_html(self, html: str, model: PageModel):
        """Extract interactive elements from HTML."""
        # Find elements with test IDs
        for attr in self.TEST_ID_ATTRS:
            pattern = rf'{attr}=["\']([^"\']+)["\']'
            for match in re.finditer(pattern, html):
                test_id = match.group(1)
                name = self._testid_to_name(test_id)

                # Determine element type
                element_type = self._infer_element_type(html, test_id)

                model.elements.append(PageElement(
                    name=name,
                    element_type=element_type,
                    selector=test_id,
                    selector_type=attr.replace('data-', ''),
                    description=f"Element: {test_id}"
                ))

        # Find buttons
        for match in re.finditer(r'<button[^>]*>([^<]+)</button>', html, re.I):
            button_text = match.group(1).strip()
            name = self._text_to_name(button_text) + "Button"

            model.elements.append(PageElement(
                name=name,
                element_type="button",
                selector=f"button:has-text('{button_text}')",
                selector_type="text",
                description=f"{button_text} button"
            ))

        # Find inputs
        for match in re.finditer(r'<input[^>]*name=["\']([^"\']+)["\']', html, re.I):
            input_name = match.group(1)
            name = self._text_to_name(input_name) + "Input"

            model.elements.append(PageElement(
                name=name,
                element_type="input",
                selector=f"input[name='{input_name}']",
                selector_type="css",
                description=f"{input_name} input field"
            ))

        # Find links
        for match in re.finditer(r'<a[^>]*>([^<]+)</a>', html, re.I):
            link_text = match.group(1).strip()
            if len(link_text) > 50:  # Skip long text
                continue

            name = self._text_to_name(link_text) + "Link"

            model.elements.append(PageElement(
                name=name,
                element_type="link",
                selector=f"a:has-text('{link_text}')",
                selector_type="text",
                description=f"{link_text} link"
            ))

    def _extract_pages_from_test(self, test_content: str) -> List[PageModel]:
        """Extract page models from test content."""
        pages = []

        # Look for page.goto() calls
        goto_pattern = r'(?:page\.goto|cy\.visit)\(["\']([^"\']+)["\']\)'
        urls = set(re.findall(goto_pattern, test_content))

        for url in urls:
            page_name = self._url_to_page_name(urlparse(url).path)

            model = PageModel(
                name=page_name,
                url=url,
                description=f"Page object for {url}"
            )

            # Extract selectors used for this page
            self._extract_selectors_from_test(test_content, model)

            pages.append(model)

        return pages if pages else [self._generate_default_page()]

    def _extract_selectors_from_test(self, test_content: str, model: PageModel):
        """Extract selectors from test file."""
        # Playwright selectors
        pw_patterns = [
            (r'page\.click\(["\']([^"\']+)["\']\)', 'button'),
            (r'page\.fill\(["\']([^"\']+)["\']', 'input'),
            (r'page\.locator\(["\']([^"\']+)["\']\)', 'element'),
        ]

        # Cypress selectors
        cy_patterns = [
            (r'cy\.get\(["\']([^"\']+)["\']\)', 'element'),
            (r'cy\.contains\(["\']([^"\']+)["\']\)', 'element'),
        ]

        patterns = pw_patterns if 'playwright' in test_content.lower() else cy_patterns

        seen_selectors = set()

        for pattern, element_type in patterns:
            for match in re.finditer(pattern, test_content):
                selector = match.group(1)

                if selector in seen_selectors:
                    continue
                seen_selectors.add(selector)

                # Generate element name
                name = self._selector_to_name(selector)

                model.elements.append(PageElement(
                    name=name,
                    element_type=element_type,
                    selector=selector,
                    selector_type="css",
                    description=f"Element: {selector}"
                ))

    def _generate_default_page(self) -> PageModel:
        """Generate a default page template."""
        model = PageModel(
            name="DefaultPage",
            url="/",
            description="Default page object template"
        )

        self._add_common_elements(model)

        return model

    def _infer_actions(self, model: PageModel):
        """Infer common actions from elements."""
        # Login action
        has_username = any("username" in e.name.lower() for e in model.elements)
        has_password = any("password" in e.name.lower() for e in model.elements)
        has_submit = any("submit" in e.name.lower() or "login" in e.name.lower() for e in model.elements)

        if has_username and has_password and has_submit:
            model.actions.append(PageAction(
                name="login",
                description="Login with username and password",
                elements_used=["usernameInput", "passwordInput", "loginButton"]
            ))

        # Search action
        has_search_input = any("search" in e.name.lower() for e in model.elements if e.element_type == "input")
        has_search_button = any("search" in e.name.lower() for e in model.elements if e.element_type == "button")

        if has_search_input:
            model.actions.append(PageAction(
                name="search",
                description="Perform search",
                elements_used=["searchInput", "searchButton"] if has_search_button else ["searchInput"]
            ))

        # Form submission
        has_inputs = len([e for e in model.elements if e.element_type == "input"]) > 1
        has_submit_button = any("submit" in e.name.lower() for e in model.elements)

        if has_inputs and has_submit_button:
            model.actions.append(PageAction(
                name="submitForm",
                description="Submit form with provided data",
                elements_used=[e.name for e in model.elements if e.element_type in ("input", "button")]
            ))

    def _testid_to_name(self, testid: str) -> str:
        """Convert test ID to camelCase name."""
        parts = re.split(r'[-_]', testid)
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])

    def _text_to_name(self, text: str) -> str:
        """Convert text to camelCase name."""
        # Remove special characters
        text = re.sub(r'[^\w\s]', '', text)
        parts = text.split()
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:]) if parts else "element"

    def _selector_to_name(self, selector: str) -> str:
        """Convert selector to camelCase name."""
        # Extract meaningful part
        if '[data-testid=' in selector or '[data-test=' in selector:
            match = re.search(r'data-test(?:id)?=["\']([^"\']+)["\']', selector)
            if match:
                return self._testid_to_name(match.group(1))

        if '#' in selector:
            return selector.split('#')[1].split('.')[0]

        if '.' in selector:
            return self._text_to_name(selector.split('.')[1].split('[')[0])

        return "element"

    def _infer_element_type(self, html: str, testid: str) -> str:
        """Infer element type from context."""
        if "button" in testid.lower() or "btn" in testid.lower():
            return "button"
        if "input" in testid.lower() or "field" in testid.lower():
            return "input"
        if "link" in testid.lower():
            return "link"
        return "element"

    def generate_code(self, model: PageModel) -> str:
        """Generate code for page object."""
        if self.language == "typescript":
            return self._generate_typescript(model)
        elif self.language == "python":
            return self._generate_python(model)
        elif self.language == "java":
            return self._generate_java(model)
        else:
            raise ValueError(f"Unsupported language: {self.language}")

    def _generate_typescript(self, model: PageModel) -> str:
        """Generate TypeScript Page Object."""
        if self.framework == "playwright":
            return self._generate_playwright_typescript(model)
        elif self.framework == "cypress":
            return self._generate_cypress_typescript(model)
        else:
            raise ValueError(f"Unsupported framework: {self.framework}")

    def _generate_playwright_typescript(self, model: PageModel) -> str:
        """Generate Playwright TypeScript Page Object."""
        code = f"""import {{ Page, Locator }} from '@playwright/test';

/**
 * {model.description}
 */
export class {model.name} {{
  readonly page: Page;

"""

        # Generate element locators
        for element in model.elements:
            selector_method = self._get_playwright_selector(element)
            code += f"  // {element.description or element.name}\n"
            code += f"  readonly {element.name}: Locator;\n\n"

        code += f"""  constructor(page: Page) {{
    this.page = page;

"""

        # Initialize locators
        for element in model.elements:
            selector_method = self._get_playwright_selector(element)
            code += f"    this.{element.name} = page.{selector_method};\n"

        code += "  }\n\n"

        # Generate goto method
        code += f"""  async goto() {{
    await this.page.goto('{model.url}');
  }}

"""

        # Generate action methods
        for action in model.actions:
            params = ""
            if "login" in action.name.lower():
                params = "username: string, password: string"
            elif "search" in action.name.lower():
                params = "query: string"
            elif "submit" in action.name.lower():
                params = "data: Record<string, string>"

            return_type = f": Promise<{action.returns_new_page}>" if action.returns_new_page else ": Promise<void>"

            code += f"""  /**
   * {action.description}
   */
  async {action.name}({params}){return_type} {{
"""

            # Generate action body
            if "login" in action.name.lower():
                code += """    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
"""
            elif "search" in action.name.lower():
                code += """    await this.searchInput.fill(query);
"""
                if any("searchButton" in e for e in action.elements_used):
                    code += "    await this.searchButton.click();\n"
                else:
                    code += "    await this.searchInput.press('Enter');\n"

            code += "  }\n\n"

        code += "}\n"

        return code

    def _generate_cypress_typescript(self, model: PageModel) -> str:
        """Generate Cypress TypeScript Page Object."""
        code = f"""/**
 * {model.description}
 */
export class {model.name} {{
"""

        # Generate element methods
        for element in model.elements:
            selector = self._get_cypress_selector(element)
            code += f"""
  // {element.description or element.name}
  get {element.name}() {{
    return cy.get('{selector}');
  }}
"""

        # Generate goto method
        code += f"""
  visit() {{
    cy.visit('{model.url}');
  }}
"""

        # Generate action methods
        for action in model.actions:
            params = ""
            if "login" in action.name.lower():
                params = "username: string, password: string"
            elif "search" in action.name.lower():
                params = "query: string"

            code += f"""
  /**
   * {action.description}
   */
  {action.name}({params}) {{
"""

            if "login" in action.name.lower():
                code += """    this.usernameInput.type(username);
    this.passwordInput.type(password);
    this.loginButton.click();
"""
            elif "search" in action.name.lower():
                code += """    this.searchInput.type(query);
"""
                if any("searchButton" in e for e in action.elements_used):
                    code += "    this.searchButton.click();\n"
                else:
                    code += "    this.searchInput.type('{enter}');\n"

            code += "  }\n"

        code += "}\n"

        return code

    def _generate_python(self, model: PageModel) -> str:
        """Generate Python Page Object for Selenium."""
        code = f"""from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class {model.name}:
    \"\"\"
    {model.description}
    \"\"\"

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

"""

        # Generate element locators
        for element in model.elements:
            locator_type, locator_value = self._get_selenium_locator(element)
            const_name = element.name.upper()
            code += f"    # {element.description or element.name}\n"
            code += f"    {const_name} = (By.{locator_type}, '{locator_value}')\n\n"

        # Generate goto method
        code += f"""    def goto(self):
        self.driver.get('{model.url}')

"""

        # Generate element access methods
        for element in model.elements:
            const_name = element.name.upper()
            code += f"""    def get_{element.name}(self):
        return self.wait.until(EC.presence_of_element_located(self.{const_name}))

"""

        # Generate action methods
        for action in model.actions:
            params = ["self"]
            if "login" in action.name.lower():
                params.extend(["username: str", "password: str"])
            elif "search" in action.name.lower():
                params.append("query: str")

            code += f"""    def {action.name}({', '.join(params)}):
        \"\"\"
        {action.description}
        \"\"\"
"""

            if "login" in action.name.lower():
                code += """        self.get_usernameInput().send_keys(username)
        self.get_passwordInput().send_keys(password)
        self.get_loginButton().click()
"""
            elif "search" in action.name.lower():
                code += """        self.get_searchInput().send_keys(query)
"""
                if any("searchButton" in e for e in action.elements_used):
                    code += "        self.get_searchButton().click()\n"
                else:
                    code += "        self.get_searchInput().send_keys('\\n')\n"

            code += "\n"

        return code

    def _generate_java(self, model: PageModel) -> str:
        """Generate Java Page Object for Selenium."""
        code = f"""import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.ExpectedConditions;
import java.time.Duration;

/**
 * {model.description}
 */
public class {model.name} {{
    private final WebDriver driver;
    private final WebDriverWait wait;

"""

        # Generate element locators
        for element in model.elements:
            locator_type, locator_value = self._get_selenium_locator(element)
            code += f"    // {element.description or element.name}\n"
            code += f"    private static final By {element.name.upper()} = By.{locator_type.lower()}(\"{locator_value}\");\n\n"

        # Constructor
        code += f"""    public {model.name}(WebDriver driver) {{
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }}

    public void goTo() {{
        driver.get("{model.url}");
    }}

"""

        # Generate element access methods
        for element in model.elements:
            method_name = f"get{element.name[0].upper() + element.name[1:]}"
            code += f"""    public WebElement {method_name}() {{
        return wait.until(ExpectedConditions.presenceOfElementLocated({element.name.upper()}));
    }}

"""

        # Generate action methods
        for action in model.actions:
            params = []
            if "login" in action.name.lower():
                params = ["String username", "String password"]
            elif "search" in action.name.lower():
                params = ["String query"]

            param_str = ", ".join(params)

            code += f"""    /**
     * {action.description}
     */
    public void {action.name}({param_str}) {{
"""

            if "login" in action.name.lower():
                code += """        getUsernameInput().sendKeys(username);
        getPasswordInput().sendKeys(password);
        getLoginButton().click();
"""
            elif "search" in action.name.lower():
                code += """        getSearchInput().sendKeys(query);
"""
                if any("searchButton" in e for e in action.elements_used):
                    code += "        getSearchButton().click();\n"
                else:
                    code += "        getSearchInput().submit();\n"

            code += "    }\n\n"

        code += "}\n"

        return code

    def _get_playwright_selector(self, element: PageElement) -> str:
        """Get Playwright selector method."""
        if element.selector_type in ("testid", "test"):
            return f"getByTestId('{element.selector}')"
        elif element.selector_type == "text":
            return element.selector.replace("has-text", "getByText")
        else:
            return f"locator('{element.selector}')"

    def _get_cypress_selector(self, element: PageElement) -> str:
        """Get Cypress selector."""
        if element.selector_type in ("testid", "test"):
            return f"[data-testid=\"{element.selector}\"]"
        else:
            return element.selector

    def _get_selenium_locator(self, element: PageElement) -> Tuple[str, str]:
        """Get Selenium locator type and value."""
        if element.selector_type in ("testid", "test"):
            return ("CSS_SELECTOR", f"[data-testid='{element.selector}']")
        elif element.selector.startswith("#"):
            return ("ID", element.selector[1:])
        elif element.selector.startswith("."):
            return ("CLASS_NAME", element.selector[1:])
        elif element.selector.startswith("//"):
            return ("XPATH", element.selector)
        else:
            return ("CSS_SELECTOR", element.selector)

    def save_page_object(self, model: PageModel):
        """Generate and save page object file."""
        code = self.generate_code(model)

        # Determine file extension
        ext_map = {
            "typescript": ".ts",
            "python": ".py",
            "java": ".java"
        }
        ext = ext_map.get(self.language, ".txt")

        # Save file
        output_file = self.output_dir / f"{model.name}{ext}"
        output_file.write_text(code)

        self.log(f"Generated: {output_file}", "SUCCESS")

        return str(output_file)


def main():
    parser = argparse.ArgumentParser(
        description="Page Object Model Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from URL
  %(prog)s --url https://example.com/login --framework playwright --language typescript

  # Generate from HTML file
  %(prog)s --html page.html --framework cypress

  # Generate from existing test
  %(prog)s --test tests/login.spec.ts --framework playwright

  # Generate with custom output directory
  %(prog)s --url https://example.com/dashboard --output-dir pages/

  # Output as JSON (structure only)
  %(prog)s --url https://example.com/login --json
        """
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    # Input sources (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--url",
        help="Generate from URL"
    )
    input_group.add_argument(
        "--html",
        help="Generate from HTML file"
    )
    input_group.add_argument(
        "--test",
        help="Generate from existing test file"
    )

    # Framework and language
    parser.add_argument(
        "--framework",
        choices=["playwright", "cypress", "selenium"],
        default="playwright",
        help="E2E testing framework (default: playwright)"
    )
    parser.add_argument(
        "--language",
        choices=["typescript", "python", "java"],
        default="typescript",
        help="Output language (default: typescript)"
    )

    # Output options
    parser.add_argument(
        "-o", "--output-dir",
        default="pages",
        help="Output directory (default: pages)"
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output page structure as JSON"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Validate framework/language compatibility
    if args.framework in ("playwright", "cypress") and args.language not in ("typescript", "javascript"):
        print(f"Warning: {args.framework} typically uses TypeScript/JavaScript", file=sys.stderr)

    if args.framework == "selenium" and args.language == "typescript":
        print("Warning: Selenium typically uses Python or Java", file=sys.stderr)

    try:
        generator = PageObjectGenerator(args)

        # Generate page model(s)
        if args.url:
            models = [generator.generate_from_url(args.url)]
        elif args.html:
            models = [generator.generate_from_html(Path(args.html))]
        elif args.test:
            models = generator.generate_from_test(Path(args.test))
        else:
            print("Error: No input source specified", file=sys.stderr)
            sys.exit(1)

        # Output results
        if args.json_output:
            output = {
                "framework": args.framework,
                "language": args.language,
                "pages": [
                    {
                        "name": m.name,
                        "url": m.url,
                        "description": m.description,
                        "elements": [
                            {
                                "name": e.name,
                                "type": e.element_type,
                                "selector": e.selector,
                                "selector_type": e.selector_type
                            }
                            for e in m.elements
                        ],
                        "actions": [
                            {
                                "name": a.name,
                                "description": a.description,
                                "elements_used": a.elements_used
                            }
                            for a in m.actions
                        ]
                    }
                    for m in models
                ]
            }
            print(json.dumps(output, indent=2))
        else:
            # Generate and save code files
            for model in models:
                generator.save_page_object(model)

            generator.log(f"\nGenerated {len(models)} page object(s)", "SUCCESS")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
