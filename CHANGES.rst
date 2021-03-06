Changelog of freq
===================================================

0.6.5 (unreleased)
------------------

- Allowing task state "STARTED" in addition to PENDING/etc.


0.6.4 (2019-04-12)
------------------

- Null values in timeseries response are converted to np.nan for the
  calculations.


0.6.3 (2018-07-04)
------------------

- Fixed url logging with task polling.


0.6.2 (2018-04-06)
------------------

- Fixed iframe width to show logos.


0.6.1 (2018-04-05)
------------------

- Fix map session for empty session.


0.6 (2018-04-04)
----------------

- Iframe allmost fullscreen for better lizard-client menus on small screens.

- Keep location on reset.


0.5 (2018-03-28)

- Added default in Organization.

- Added full organisation name as title attribute on organisation pulldown.

- Changed "no data available" placeholder text.

- Keeps timeseries selection menu visible even when a timeseries is selected.

- Removes timeseries data when timeseries is selected.


0.4 (2016-10-06)
----------------

- Added wait-spinner on timeseries analysis page.

- Updates organisations request to match newly updated sso.


0.3.3 (2016-10-03)
------------------

- Rollback freq calculator changes.


0.3.2 (2016-09-29)
------------------

- Fixes iframe url.
- Fixes title for ihp logo.


0.3.1 (2016-09-28)
------------------

- Fixes IFRAME_BASE_URL.


0.3 (2016-09-28)
----------------

- Makes IFRAME_BASE_URL a setting.
- Fixes harmonics (harmonics 1 is correct again)


0.2 (2016-04-19)
----------------
- bugfixes


0.1 (2016-04-12)
----------------
- Added correllogram to autoregressive model.
- All dropdowns now hover over map.
- Layer selection on map only in map, not in Freq.
- Faster loading
- Load image (wait spinner) for map
- maps with layers
- dropdowns over map
- improved freq with a change in graphs. Removed one spinner accordingly.

- Initial project structure created with nensskel 1.37.dev0.
