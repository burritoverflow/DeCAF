import requests
import sys
import argparse
from difflib import get_close_matches
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

# Colors are important
init(autoreset=True)

def load_requirements(requirements_file):
    packages = []
    with open(requirements_file, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#'):
                package = line.split('==')[0]
                packages.append(package)
    return packages

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

def find_similar_packages(package_name, package_list, cutoff=0.8):
    package_name_lower = package_name.lower()
    package_list_lower = [pkg.lower() for pkg in package_list]
    similar_indices = get_close_matches(package_name_lower, package_list_lower, n=5, cutoff=cutoff)
    # Map back to original casing
    similar_packages = [package_list[package_list_lower.index(pkg)] for pkg in similar_indices]
    return similar_packages

def main(requirements_file, allowlist_file):
    print("Loading packages from requirements file...")
    packages = load_requirements(requirements_file)
    allowlist = load_allowlist(allowlist_file)
    potential_risks = []
    typo_alerts = []

    # Load PyPI package list once
    pypi_packages = get_pypi_package_list()

    for package in packages:
        package_lower = package.lower()

        # Skip, allowed
        if package_lower in allowlist:
            print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Package '{package}' is in the allowlist. Skipping.")
            continue

        # Check for typos by comparing to the allowlist
        possible_typos = find_similar_packages(package, list(allowlist), cutoff=0.8)
        if possible_typos:
            print(f"{Fore.CYAN}[TYPO ALERT]{Style.RESET_ALL} Package '{package}' in requirements.txt may be a typo for: {possible_typos}")
            typo_alerts.append((package, possible_typos))
            continue

        print(f"Checking package: {package}")
        if check_pypi(package):
            print(f"{Fore.RED}[ALERT]{Style.RESET_ALL} Package '{package}' exists on PyPI.")
            potential_risks.append(package)
        else:
            # Now check for similar packages on PyPI
            # (typosquatting)
            similar_packages = find_similar_packages(package, pypi_packages)
            similar_packages = [pkg for pkg in similar_packages if pkg.lower() not in allowlist]
            if similar_packages:
                print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} Found similar packages on PyPI for '{package}': {similar_packages}")
                potential_risks.extend(similar_packages)

    # Summary of Typo Alerts
    if typo_alerts:
        print(f"\n{Fore.CYAN}Potential typos detected in requirements.txt:{Style.RESET_ALL}")
        for typo_package, suggestions in typo_alerts:
            print(f"- '{typo_package}' may be a typo for: {', '.join(suggestions)}")

    # Summary of Dependency Confusion Risks
    if potential_risks:
        print(f"\n{Fore.RED}Potential dependency confusion or typosquatting risks detected:{Style.RESET_ALL}")
        for risk in set(potential_risks):
            print(f"- {risk}")
            
    else:
        print("\nNo potential dependency confusion or typosquatting risks detected.")

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Detect dependency confusion, typosquatting, and typos in requirements.txt.')
    parser.add_argument('requirements', help='Path to the requirements.txt file.')
    parser.add_argument('--allowlist', help='Path to the allowlist file.', default='allowlist.txt')
    args = parser.parse_args()
    main(args.requirements, args.allowlist)
