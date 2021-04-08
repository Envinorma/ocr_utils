import alto


def assert_one_page_and_get_it(file_: alto.Alto) -> alto.Page:
    assert len(file_.layout.pages) == 1, f'Expecting 1 page in alto file, got {len(file_.layout.pages)}'
    return file_.layout.pages[0]
