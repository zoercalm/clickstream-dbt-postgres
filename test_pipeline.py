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
            self.assertEqual(c.execute('select count(*),sum(orders) from reporting.cart_journey').fetchone(),(12,6))
            self.assertEqual(c.execute('select distinct first_cart_source,last_cart_source from reporting.cart_journey').fetchall(),[('product','search')])
        run(A,B)
        run(A,A,count=2)
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
if __name__=='__main__':unittest.main()
