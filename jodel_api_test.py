import jodel_api

def test_1():
    assert 5 == 5

def test_2():
    assert jodel_api.JodelAccount.version == 'android_4.37.2'

def test_3():
    j = jodel_api.JodelAccount(48.144378, 11.573044, "Munich")
    r = j.get_posts_recent()

    assert r[0] == 200
