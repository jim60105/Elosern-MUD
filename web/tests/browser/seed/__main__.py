"""``python -m web.tests.browser.seed`` entry point.

The former single module ran its ``main()`` under ``__main__``; the
package keeps the exact command line via this alias.
"""

from web.tests.browser.seed.runner import main


main()
