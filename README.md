# DeCAF

## The Dependency Confusion Attack Finder (DeCAF) is a Python-based tool developed to help detect potential dependency confusion and typosquatting vulnerabilities in Python projects.

In early 2021, a security researcher named Alex Birsan discovered a novel supply chain attack vector called dependency confusion. This attack exploits the way package managers resolve dependencies, potentially allowing malicious code to infiltrate software projects. DeCAF attempts to assist in finding potentially malicious packages for Python projects based on the requirements.txt file.

## Usage:

> python decaf.py requirements.txt --allowlist allowlist.txt

DeCAF includes a sample allowlist with 148 of the most common python packages available in hopes of deterring false positives. Including the allowlist is optional. If an allowlist is not specified, the default allowlist will be applied. To use a custom allowlist, just supply a path to the txt file.

DeCAF also includes a sample requirements file, 'test_requirements.txt'.

Quite simply, DeCAF works in these steps:

1.	Load Dependencies: Reads the requirements.txt file to gather all package names used in the project.
2.	Load Allowlist: Reads an allowlist file containing known legitimate packages to exclude from alerts.
3.	Typo Detection: Compares package names in requirements.txt against the allowlist (known good) to identify potential typos.
4.	Dependency Confusion Checks: For packages not in the allowlist or typo list, checks if they exist on PyPI.
5.	Typosquatting Checks: Searches for packages with similar names on PyPI to detect possible typosquatting attempts.
6.	Reporting: Generates alerts with color-coded messages to indicate the severity and type of each finding.

## Output:

### [TYPO ALERT] (Cyan): Potential typos in requirements.txt.
### [ALERT] (Red): Exact package name exists on PyPI (dependency confusion risk).
### [WARNING] (Yellow): Similar package names found on PyPI (typosquatting risk).
### [INFO] (Green): Package is in the allowlist and skipped.

## Screenshot:
![alt text](image.png)