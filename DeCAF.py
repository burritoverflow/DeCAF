import requests
import sys
import argparse
import json
from difflib import get_close_matches
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

init(autoreset=True)

def load_requirements_pip(requirements_file):
    packages = []
    with open(requirements_file, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#'):
                package = line.split('==')[0]
                packages.append(package)
    return packages

def load_dependencies_npm(package_json_file):
    with open(package_json_file, 'r') as file:
        data = json.load(file)
    dependencies = data.get('dependencies', {})
    dev_dependencies = data.get('devDependencies', {})
    all_dependencies = {**dependencies, **dev_dependencies}
    return list(all_dependencies.keys())

def load_allowlist(allowlist_file):
    allowlist = set()
    try:
        with open(allowlist_file, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    allowlist.add(line.lower())
    except FileNotFoundError:
        print(f"No allowlist file found at '{allowlist_file}'. Continuing without an allowlist.")
    return allowlist

def check_pypi(package_name):
    try:
        response = requests.get(f'https://pypi.org/pypi/{package_name}/json')
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"Error checking PyPI for package '{package_name}': {e}")
        return False

def check_npm_registry(package_name):
    try:
        response = requests.get(f'https://registry.npmjs.org/{package_name}')
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"Error checking npm registry for package '{package_name}': {e}")
        return False

def find_similar_packages_pypi(package_name, package_list, cutoff=0.8):
    package_name_lower = package_name.lower()
    package_list_lower = [pkg.lower() for pkg in package_list]
    similar_indices = get_close_matches(package_name_lower, package_list_lower, n=5, cutoff=cutoff)
    # Map back to original casing
    similar_packages = [package_list[package_list_lower.index(pkg)] for pkg in similar_indices]
    return similar_packages

def find_similar_packages_npm(package_name):
    try:
        response = requests.get(f'https://api.npms.io/v2/search/suggestions?q={package_name}')
        if response.status_code != 200:
            print("Error accessing npm search API.")
            return []
        results = response.json()
        similar_packages = [pkg['package']['name'] for pkg in results]
        return similar_packages
    except requests.RequestException as e:
        print(f"Error fetching package suggestions from npm: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def get_pypi_package_list():
    # Retrieve the list of all packages from PyPI simple index
    try:
        response = requests.get('https://pypi.org/simple/')
        if response.status_code != 200:
            print("Error accessing PyPI simple index.")
            sys.exit(1)
        soup = BeautifulSoup(response.text, 'html.parser')
        all_packages = [link.text for link in soup.find_all('a')]
        return all_packages
    except requests.RequestException as e:
        print(f"Error fetching package list from PyPI: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='DECAF: Dependency Confusion Attack Finder for pip and npm.')
    parser.add_argument('package_file', help='Path to the requirements.txt or package.json file.')
    parser.add_argument('--package-manager', '-pm', choices=['pip', 'npm'], required=True, help='Specify the package manager (pip or npm).')
    parser.add_argument('--allowlist', '-al', help='Path to the allowlist file.', default='allowlist.txt')
    args = parser.parse_args()

    package_manager = args.package_manager
    package_file = args.package_file
    allowlist_file = args.allowlist

    if package_manager == 'pip':
        print("Loading packages from requirements.txt...")
        packages = load_requirements_pip(package_file)
    elif package_manager == 'npm':
        print("Loading dependencies from package.json...")
        packages = load_dependencies_npm(package_file)
    else:
        print("Unsupported package manager.")
        sys.exit(1)

    allowlist = load_allowlist(allowlist_file)
    potential_risks = []
    typo_alerts = []

    if package_manager == 'pip':
        pypi_packages = get_pypi_package_list()
    elif package_manager == 'npm':
        pypi_packages = []  # Not used for npm

    for package in packages:
        package_lower = package.lower()

        if package_lower in allowlist:
            print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Package '{package}' is in the allowlist. Skipping.")
            continue

        # Check for typos by comparing to the allowlist
        possible_typos = get_close_matches(package_lower, allowlist, n=5, cutoff=0.8)
        if possible_typos:
            print(f"{Fore.CYAN}[TYPO ALERT]{Style.RESET_ALL} Package '{package}' may be a typo for: {possible_typos}")
            typo_alerts.append((package, possible_typos))
            continue

        print(f"Checking package: {package}")
        if package_manager == 'pip':
            if check_pypi(package):
                print(f"{Fore.RED}[ALERT]{Style.RESET_ALL} Package '{package}' exists on PyPI.")
                potential_risks.append(package)
            else:
                # Check for similar packages on PyPI (typosquatting)
                similar_packages = find_similar_packages_pypi(package, pypi_packages)
                similar_packages = [pkg for pkg in similar_packages if pkg.lower() not in allowlist]
                if similar_packages:
                    print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} Found similar packages on PyPI for '{package}': {similar_packages}")
                    potential_risks.extend(similar_packages)
        elif package_manager == 'npm':
            if check_npm_registry(package):
                print(f"{Fore.RED}[ALERT]{Style.RESET_ALL} Package '{package}' exists on npm registry.")
                potential_risks.append(package)
            else:
                # Check for similar packages on npm (typosquatting)
                similar_packages = find_similar_packages_npm(package)
                similar_packages = [pkg for pkg in similar_packages if pkg.lower() not in allowlist]
                if similar_packages:
                    print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} Found similar packages on npm for '{package}': {similar_packages}")
                    potential_risks.extend(similar_packages)

    # Summary of Typo Alerts
    if typo_alerts:
        print(f"\n{Fore.CYAN}Potential typos detected in your package file:{Style.RESET_ALL}")
        for typo_package, suggestions in typo_alerts:
            print(f"- '{typo_package}' may be a typo for: {', '.join(suggestions)}")

    # Summary of Dependency Confusion Risks
    if potential_risks:
        print(f"\n{Fore.RED}Potential dependency confusion or typosquatting risks detected:{Style.RESET_ALL}")
        for risk in set(potential_risks):
            print(f"- {risk}")
    else:
        print("\nNo potential dependency confusion or typosquatting risks detected.")

if __name__ == "__main__":
    main()