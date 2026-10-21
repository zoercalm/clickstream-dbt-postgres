import unittest
from datetime import date
from pipeline import connect,run,LOCK
A=date(2026,1,1);B=date(2026,1,3)
class Integration(unittest.TestCase):
    def setUp(self):
        with connect() as c:
            c.execute('DROP SCHEMA IF EXISTS reporting CASCADE');c.execute('DROP SCHEMA IF EXISTS raw CASCADE')
    def test_repeat_and_range_removal(self):
        run(A,B)
        with connect() as c:
            self.assertEqual(c.execute('select count(*),sum(orders) from reporting.cart_journey').fetchone(),(12,9))
            self.assertEqual(c.execute('select first_cart_source,last_cart_source,cart_entries,orders from reporting.cart_journey order by visit_id limit 4').fetchall(),[(None,None,0,0),('product','search',2,1),('email','email',1,2),('product','search',2,0)])
        run(A,B)
        run(A,A,batch="revised",count=2)
        with connect() as c:
            self.assertEqual(c.execute('select count(*) from reporting.cart_journey').fetchone()[0],10)
            self.assertEqual(c.execute('select count(*) from raw.hits h left join raw.visits v using(visit_id) where v.visit_id is null').fetchone()[0],0)
    def test_resume_after_committed_chunk(self):
        with self.assertRaises(RuntimeError):run(A,B,batch='interrupted',fail_after=1)
        with connect() as c:self.assertEqual(c.execute('select count(*) from raw.checkpoints').fetchone()[0],1)
        run(A,B,batch='interrupted',resume=True)
        with connect() as c:
            self.assertEqual(c.execute('select count(*) from raw.checkpoints').fetchone()[0],3)
            self.assertEqual(c.execute('select count(*) from reporting.cart_journey').fetchone()[0],12)
    def test_concurrent_writer_rejected(self):
        with connect() as c:
            c.execute('select pg_advisory_lock(%s)',(LOCK,))
            try:
                with self.assertRaisesRegex(RuntimeError,'another pipeline'):run(A,B)
            finally:c.execute('select pg_advisory_unlock(%s)',(LOCK,))
    def test_invalid_range(self):
        with self.assertRaises(ValueError):run(B,A)
    def test_empty_day_replaces_old_rows(self):
        run(A,B)
        run(A,A,batch='empty',count=0)
        with connect() as c:
            self.assertEqual(c.execute('select count(*) from reporting.cart_journey').fetchone()[0],8)
            self.assertEqual(c.execute('select count(*) from raw.visits where day=%s',(A,)).fetchone()[0],0)
    def test_changed_resume_parameters_rejected(self):
        with self.assertRaises(RuntimeError):run(A,B,batch='resume',fail_after=1)
        for kwargs in [dict(count=2),dict(end=A)]:
            options=dict(start=A,end=B,batch='resume',resume=True);options.update(kwargs)
            with self.assertRaisesRegex(ValueError,'parameters changed'):run(**options)
        with connect() as c:
            self.assertEqual(c.execute('select count(*) from raw.checkpoints').fetchone()[0],1)
        run(A,B,batch='resume',resume=True)
    def test_unknown_resume_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown resume'):run(A,B,batch='unknown',resume=True)
if __name__=='__main__':unittest.main()

