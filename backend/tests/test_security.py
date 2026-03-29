from security import validate_url, verify_api_key


def test_valid_tiktok_url():
    assert validate_url("https://www.tiktok.com/@user/video/123") is True


def test_valid_youtube_shorts_url():
    assert validate_url("https://youtube.com/shorts/abc123") is True


def test_valid_douyin_url():
    assert validate_url("https://www.douyin.com/video/123") is True


def test_valid_xiaohongshu_url():
    assert validate_url("https://www.xiaohongshu.com/explore/123") is True


def test_valid_pinterest_url():
    assert validate_url("https://www.pinterest.com/pin/123") is True


def test_valid_facebook_url():
    assert validate_url("https://www.facebook.com/reel/123") is True


def test_reject_http_url():
    assert validate_url("http://tiktok.com/video/123") is False


def test_reject_unknown_domain():
    assert validate_url("https://evil.com/video") is False


def test_reject_empty_url():
    assert validate_url("") is False


def test_reject_non_url():
    assert validate_url("not a url") is False


def test_valid_api_key():
    assert verify_api_key("test-secret-key", "test-secret-key") is True


def test_invalid_api_key():
    assert verify_api_key("wrong-key", "test-secret-key") is False
