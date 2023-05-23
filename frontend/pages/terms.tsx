import Navbar from '@/components/Navbar';
import { GetServerSidePropsContext } from 'next';
import {
  createServerSupabaseClient,
  User
} from '@supabase/auth-helpers-nextjs';
import Terms from '@/components/Terms';

interface Props {
  user: User;
}

export default function TermsPage({ user }: Props) {
  return (
    <>
      <Navbar user={user} />
      <Terms />
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
