import { useRouter } from 'next/router';
import { useEffect } from 'react';
import { useUser, useSupabaseClient } from '@supabase/auth-helpers-react';
import { Auth } from '@supabase/auth-ui-react';
import { ThemeSupa } from '@supabase/auth-ui-shared';
import { Heading } from '@chakra-ui/react';
import NextLink from 'next/link';

import LoadingDots from '@/components/ui/LoadingDots';
import { getURL } from '@/utils/helpers';

const SignIn = () => {
  const router = useRouter();
  const user = useUser();
  const supabaseClient = useSupabaseClient();

  useEffect(() => {
    if (user) {
      router.replace('/');
    }
  }, [user]);

  if (!user)
    return (
      <div className="flex justify-center height-screen-helper">
        <div className="flex flex-col justify-between max-w-lg p-3 m-auto w-80">
          <Heading as={NextLink} href="/">
            Scribe
          </Heading>
          <div className="flex flex-col space-y-4">
            <Auth
              supabaseClient={supabaseClient}
              providers={[]}
              redirectTo={getURL()}
              appearance={{
                theme: ThemeSupa,
                variables: {
                  default: {
                    colors: {
                      brand: '#000000',
                      brandAccent: '#000000'
                    }
                  }
                }
              }}
              theme="dark"
            />
          </div>
        </div>
      </div>
    );

  return (
    <div className="m-6 flex justify-center items-center height-screen-helper">
      <LoadingDots />
    </div>
  );
};

export default SignIn;
