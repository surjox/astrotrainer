# IAU Constellation Abbreviation Mapping

Real-sky photograph assets use official IAU three-letter constellation
abbreviations as filenames (lowercase). The same filename identifies the same
constellation in both the `unannotated/` and `annotated/` directories.

## Directory layout

```
public/images/constellations/real-sky/
  unannotated/
    {abbreviation}.{ext}   # unannotated photograph
  annotated/
    {abbreviation}.{ext}   # photograph with constellation lines drawn
```

Supported extensions: `.webp`, `.jpg`, `.jpeg`, `.png` (probed in that order).

## Abbreviation → Constellation mapping (all 88 IAU constellations)

| Abbreviation | Constellation       | Abbreviation | Constellation      | Abbreviation | Constellation       |
|-------------|---------------------|-------------|--------------------|-------------|---------------------|
| and         | Andromeda           | hya         | Hydra              | psa         | Piscis Austrinus    |
| ant         | Antlia              | hyi         | Hydrus             | pup         | Puppis              |
| aps         | Apus                | ind         | Indus              | pyx         | Pyxis               |
| aqr         | Aquarius            | lac         | Lacerta            | ret         | Reticulum           |
| aql         | Aquila              | leo         | Leo                | sge         | Sagitta             |
| ara         | Ara                 | lmi         | Leo Minor          | sgr         | Sagittarius         |
| ari         | Aries               | lep         | Lepus              | sco         | Scorpius            |
| aur         | Auriga              | lib         | Libra              | scl         | Sculptor            |
| boo         | Bootes              | lup         | Lupus              | sct         | Scutum              |
| cae         | Caelum              | lyn         | Lynx               | ser         | Serpens             |
| cam         | Camelopardalis      | lyr         | Lyra               | sex         | Sextans             |
| cnc         | Cancer              | men         | Mensa              | tau         | Taurus              |
| cvn         | Canes Venatici      | mic         | Microscopium       | tel         | Telescopium         |
| cma         | Canis Major         | mon         | Monoceros          | tri         | Triangulum          |
| cmi         | Canis Minor         | mus         | Musca              | tra         | Triangulum Australe |
| cap         | Capricornus         | nor         | Norma              | tuc         | Tucana              |
| car         | Carina              | oct         | Octans             | uma         | Ursa Major          |
| cas         | Cassiopeia          | oph         | Ophiuchus          | umi         | Ursa Minor          |
| cen         | Centaurus           | ori         | Orion              | vel         | Vela                |
| cep         | Cepheus             | pav         | Pavo               | vir         | Virgo               |
| cet         | Cetus               | peg         | Pegasus            | vol         | Volans              |
| cha         | Chamaeleon          | per         | Perseus            | vul         | Vulpecula           |
| cir         | Circinus            | phe         | Phoenix            |             |                     |
| col         | Columba             | pic         | Pictor             |             |                     |
| com         | Coma Berenices      | psc         | Pisces             |             |                     |
| cra         | Corona Australis    |             |                    |             |                     |
| crb         | Corona Borealis     |             |                    |             |                     |
| crv         | Corvus              |             |                    |             |                     |
| crt         | Crater              |             |                    |             |                     |
| cru         | Crux                |             |                    |             |                     |
| cyg         | Cygnus              |             |                    |             |                     |
| del         | Delphinus           |             |                    |             |                     |
| dor         | Dorado              |             |                    |             |                     |
| dra         | Draco               |             |                    |             |                     |
| equ         | Equuleus            |             |                    |             |                     |
| eri         | Eridanus            |             |                    |             |                     |
| for         | Fornax              |             |                    |             |                     |
| gem         | Gemini              |             |                    |             |                     |
| gru         | Grus                |             |                    |             |                     |
| her         | Hercules            |             |                    |             |                     |
| hor         | Horologium          |             |                    |             |                     |

## Asset notes

- The directories currently contain only `.gitkeep` files. Real-sky
  photographs must be supplied manually — place one file per variant per
  constellation using the lowercase IAU abbreviation as the filename.
- `src/lib/astro/constellationImages.ts` is the single centralized resolver;
  components should import `resolveConstellationImage` and
  `isConstellationImageAvailable` rather than hardcoding paths.
- `getEligibleConstellationIds()` returns constellation IDs that have an
  available unannotated photograph, used to gate Real-Sky Challenge question
  generation.