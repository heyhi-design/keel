# Security Policy

Keel is a template and documentation repository: text files, YAML schemas, and Python
scripts you run locally. There is no hosted service and no runtime this project operates on your
behalf, which limits the attack surface, but issues are still possible (a template that encourages
an unsafe pattern, a script with a real vulnerability, a dependency with a known issue).

## Reporting a vulnerability

Please report security issues privately rather than opening a public issue. Email
**hello@heyhi.design** with:

- A description of the issue and its potential impact.
- Steps to reproduce, if applicable.
- Any suggested fix or mitigation you already have in mind.

We'll acknowledge your report and follow up with next steps. Please give us reasonable time to
address the issue before any public disclosure.

## Scope

In scope: the templates, scripts, and CI configuration in this repository. Out of scope: your own
filled-in instance, your own agent runtime, and any third-party service you connect this scaffold
to.
