# GitHub Actions — Política SHA-pinning (R4)

**Regla: TODAS las `uses:` en `.github/workflows/` van pinned a commit SHA completo con comment de versión.**

```yaml
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
```

## Por qué
Refs por tag (`@v4`) son mutables: un tag comprometido en upstream ejecuta código
atacante en nuestro CI (vector supply-chain MoYu/BADBOX, case study card 3bb1f21e §6 R4).

## Cómo pinear una action nueva
1. Resuelve el commit SHA del tag (los tags anotados requieren dereference):
   ```bash
   gh api repos/OWNER/REPO/git/ref/tags/vX.Y.Z --jq '.object.sha'
   # si .object.type == "tag" (anotado):
   gh api repos/OWNER/REPO/git/tags/<sha-anterior> --jq '.object.sha'
   ```
2. Escribe `uses: OWNER/REPO@<40-hex> # vX.Y.Z`

## Verificación (CI/grep)
```bash
grep -rh 'uses:' .github/workflows/ | grep -vcE '@[0-9a-f]{40}'   # debe ser 0
```

## Actualización de versions
Bump = resolver SHA del nuevo tag + PR (el comment muestra la versión — revisor
verifica que el SHA corresponde al tag del comment).

Aplicado 2026-08-25 (card fd02f770): 130 refs en 10 workflows.
Precedente: fix SHAs rotos (card edbd4a58).
