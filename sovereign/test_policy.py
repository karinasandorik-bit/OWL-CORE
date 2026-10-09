from policy import Grant,authorize,verified_income
def test_default_deny():
    assert authorize("transfer_funds","wallet",100) is False
    assert authorize("unknown","*",100) is False
def test_bounded_grant():
    grant=Grant("production_deploy","owl-staging",200,True)
    assert authorize("production_deploy","owl-staging",100,grant)
    assert not authorize("production_deploy","kisa-production",100,grant)
    assert not authorize("production_deploy","owl-staging",200,grant)
def test_income_requires_settlement():
    assert not verified_income(100,None,True)
    assert not verified_income(100,"tx1",False)
    assert verified_income(100,"tx1",True)
if __name__=="__main__":
    test_default_deny();test_bounded_grant();test_income_requires_settlement();print("POLICY_TESTS_PASS")
