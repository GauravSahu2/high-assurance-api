
def test_bola_authorized_access_own_resource(client, token_factory):
    headers = {"Authorization": f"Bearer {token_factory('user_1')}"}
    res = client.get("/api/users/user_1", headers=headers)
    assert res.status_code == 200

def test_bola_unauthorized_access_other_resource(client, token_factory):
    headers = {"Authorization": f"Bearer {token_factory('user_2')}"}
    res = client.get("/api/users/user_1", headers=headers)
    assert res.status_code == 403

def test_bola_admin_access_override(client, token_factory):
    headers = {"Authorization": f"Bearer {token_factory('admin', 'admin')}"}
    res = client.get("/api/users/user_1", headers=headers)
    assert res.status_code == 200
