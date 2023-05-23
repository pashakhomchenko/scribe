import { ProductWithPrice } from 'types';
import { GetServerSidePropsContext } from 'next';
import {
  createServerSupabaseClient,
  User
} from '@supabase/auth-helpers-nextjs';
import { useUser } from '@/utils/useUser';
import { getActiveProductsWithPrices } from '@/utils/supabase-client';
import Landing from '@/components/Landing';
import Navbar from '@/components/Navbar';
import Pricing from '@/components/Pricing';
import GetSummary from '@/components/GetSummary';
import Footer from '@/components/Footer';

interface Props {
  user: User;
  products: ProductWithPrice[];
}

export default function Home({ user, products }: Props) {
  const { subscription, isLoading } = useUser();
  if (user && isLoading) return null;

  return (
    <>
      <Navbar user={user} />
      {!user && <Landing user={user} products={products} />}
      {user && !subscription && <Pricing products={products} />}
      {user && subscription && <GetSummary />}
      <Footer />
    </>
  );
}

export const getServerSideProps = async (ctx: GetServerSidePropsContext) => {
  const supabase = createServerSupabaseClient(ctx);
  const products = await getActiveProductsWithPrices();
  const {
    data: { session }
  } = await supabase.auth.getSession();

  if (!session)
    return {
      props: {
        initialSession: null,
        user: null,
        products: products
      }
    };

  return {
    props: {
      initialSession: session,
      user: session.user,
      products: products
    }
  };
};
