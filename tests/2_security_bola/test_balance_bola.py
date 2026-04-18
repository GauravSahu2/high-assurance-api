
def test_user_can_read_own_balance(client, token_factory):
    headers = {"Authorization": f"Bearer {token_factory('user_1')}"}
    res = client.get("/api/accounts/user_1/balance", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["user_id"] == "user_1"

def test_user_cannot_read_other_balance(client, token_factory):
    headers = {"Authorization": f"Bearer {token_factory('user_2')}"}
    res = client.get("/api/accounts/user_1/balance", headers=headers)
    assert res.status_code == 403

def test_admin_can_read_any_balance(client, token_factory):
    headers = {"Authorization": f"Bearer {token_factory('admin', 'admin')}"}
    res = client.get("/api/accounts/user_1/balance", headers=headers)
    assert res.status_code == 200
