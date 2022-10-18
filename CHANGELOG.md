# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.4.0] - 2022-10-18
### Changed
- Optional language selection

## [0.3.0] - 2022-10-14
### Changed
- Parse git.html in preference to Git Reference aka index.html
- Document type now derived from git.html section headings
- Strip 'git-' from command names
- Docs added to DB after all docs downloaded
### Fixed
- Various corrections, see misc_fixes()
- Unwanted aliases 
  
## [0.2.0] - 2022-09-25
### Changed
- Add docs recursively, after examining page links for missing docs.
- Tidied.

### Fixed
- Write docs with iso-8859-1 encoding.

## [0.1.0] - 2022-09-15
### Changed
- Converted to Python 3.
- Added 'Guides' branch.
