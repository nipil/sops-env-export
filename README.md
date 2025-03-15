# SOPS-ENV-EXPORT

Generates os-specific "source-able" terminal statements from SOPS encrypted environment files

1. When using POSIX shells, it can be used to :

- merge multiple environments at once, in the given order
- dynamically source SOPS-encrypted files into the current shell without writing secrets to the disk

      . <(./sops-env-export.py samples/crypted/sample.sops.json samples/crypted/sample.sops.yaml)

      env | sort

1. When using Windows PowerShell, it can be used to :

- merge multiple environments at once, in the given order
- decrypt the resulting environment patch to stdout, eventually writing it to disk for later sourcing (via `.`)

      python.exe .\sops-env-export.py samples/crypted/sample.sops.json samples/crypted/sample.sops.yaml > a.ps1

      . a.ps1

      Get-ChildItem env:* | Sort-Object name
      Name                           Value
      ----                           -----
      BAR                            bar'yaml
      BAZ                            baz'yaml
      FOO                            foo'yaml

# Usage

Without arguments : print the environment the python script runs in, as JSON on stdout

With SOPS file paths as argument : re-executes (without argument) through `SOPS exec-env $files`

# Prerequisites

Get one of the versions of SOPS at https://github.com/getsops/sops/releases :

    winget install --source winget --exact --id SecretsOPerationS.SOPS

Install GnuPG for encryption/decryption of example files :

    winget install --source winget --exact --id GnuPG.Gpg4win

Restart your IDE and terminals to discover the new binaries

# Samples

A dedicated key has been generated and used to encrypt the samples, like this :

    # generation
    gpg --full-generate-key
        (9) ECC (sign and encrypt) *default*
        (1) Curve 25519 *default*
        10y
        sops-env-export-development-samples
        no passphrase

    # result
    pub   ed25519 2025-03-15 [SC] [expire : 2035-03-13]
          CF5FDB6C3BD8937A20806340DA79102D48C9C72E
    uid                      sops-env-export-development-samples
    sub   cv25519 2025-03-15 [E] [expire : 2035-03-13]

    # export
    gpg --armor --export-secret-key --armor --output dev-key.asc CF5FDB6C3BD8937A20806340DA79102D48C9C72E

    # crypt samples using the dev key, as configured in `.sops.yaml` :
    sops --encrypt --output samples/crypted/sample.sops.json samples/clear/sample.json
    sops --encrypt --output samples/crypted/sample.sops.yaml samples/clear/sample.yaml
    sops --encrypt --output samples/crypted/sample.sops.env samples/clear/sample.env

Import this "well-known" encryption/decryption key for use during testing, and try to decode the samples :

    gpg --armor --import dev-key.asc

    sops -d samples/crypted/sample.sops.json
    sops -d samples/crypted/sample.sops.yaml
    sops -d samples/crypted/sample.sops.env

# Known limitations

- SOPS `exec-env` feature does not work with INI files, as these always have a "section" (even if absent),
  which makes them a "complex" document (hierarchical), instead of a "flat" one (which is what `exec-env` requires).

- On Windows, the prompt env var (`echo $env:PROMPT` seems detected as a change if it was not already set beforehand.
