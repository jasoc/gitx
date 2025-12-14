# gitx — git with superpowers

```bash
gitx clone jasoc/gitx
gitx code mylabel --branch develop
gitx go mylabel

gitx branch list jasoc/gitx
gitx branch add jasoc/gitx develop
gitx branch remove jasoc/gitx develop

gitx workspace list
gitx workspace remove jasoc/gitx
gitx workspace label jasoc/gitx mylabel

gitx config show
gitx config get defaults.editor
gitx config set defaults.editor
```

### Installation (Linux/macOS):

```bash
curl -sfL https://gitx.parisius.dev | sh -
```

Install from source

```bash
git clone https://github.com/jasoc/gitx.git
cd gitx
make install
```

### Local development

#### Requirements
- Only Docker and bash

Simply use the script

```bash
./gitx <any argument accepted>
```

from the root of the repo. It will spawn a python virtual environment and install all dependencies.
