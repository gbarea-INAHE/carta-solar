from carta_solar.branding import AUTHORS, CREDIT_LINE, INSTITUTION, available_logos


def test_credit_line_contains_authors_and_institution():
    assert "Gustavo Barea" in AUTHORS
    assert "Carolina Ganem" in AUTHORS
    assert "INAHE" in INSTITUTION
    assert "CONICET" in INSTITUTION
    assert AUTHORS in CREDIT_LINE
    assert INSTITUTION in CREDIT_LINE


def test_available_logos_returns_existing_files_only():
    logos = available_logos()
    assert isinstance(logos, list)
    assert all(path.is_file() for path in logos)
