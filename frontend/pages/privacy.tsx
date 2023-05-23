import Navbar from '@/components/Navbar';
import PrivacyPolicy from '@/components/PrivacyPolicy';
import { GetServerSidePropsContext } from 'next';
import {
  createServerSupabaseClient,
  User
} from '@supabase/auth-helpers-nextjs';

interface Props {
  user: User;
}

export default function Privacy({ user }: Props) {
  return (
    <>
      <Navbar user={user} />
      <PrivacyPolicy />
    </>
  );
}

export const getServerSideProps = async (ctx: GetServerSidePropsContext) => {
  const supabase = createServerSupabaseClient(ctx);
  const {
    data: { session }
  } = await supabase.auth.getSession();

  if (!session)
    return {
      props: {
        initialSession: null,
        user: null
      }
    };

  return {
    props: {
      initialSession: session,
      user: session.user
    }
  };
};
