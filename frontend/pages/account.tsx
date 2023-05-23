import { useState, ReactNode } from 'react';
import { GetServerSidePropsContext } from 'next';
import {
  createServerSupabaseClient,
  User
} from '@supabase/auth-helpers-nextjs';
import { useRouter } from 'next/router';
import { useSupabaseClient } from '@supabase/auth-helpers-react';

import { useUser } from '@/utils/useUser';
import { postData } from '@/utils/helpers';
import AccountForm from '@/components/AccountForm';
import Navbar from '@/components/Navbar';
import {
  Box,
  Button,
  Divider,
  Heading,
  Text,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon
} from '@chakra-ui/react';
interface Props {
  title: string;
  description?: string;
  footer?: ReactNode;
  children: ReactNode;
}

function Card({ title, description, footer, children }: Props) {
  return (
    <div className="border border-zinc-700 max-w-3xl w-full p rounded-md m-auto my-8">
      <div className="px-5 py-4">
        <h3 className="text-2xl mb-1 font-medium">{title}</h3>
        <p className="text-zinc-300">{description}</p>
        {children}
      </div>
      <div className="border-t p-4 rounded-b-md">{footer}</div>
    </div>
  );
}

export const getServerSideProps = async (ctx: GetServerSidePropsContext) => {
  const supabase = createServerSupabaseClient(ctx);
  const {
    data: { session }
  } = await supabase.auth.getSession();

  if (!session)
    return {
      redirect: {
        destination: '/signin',
        permanent: false
      }
    };

  return {
    props: {
      initialSession: session,
      user: session.user
    }
  };
};

export default function Account({ user }: { user: User }) {
  const router = useRouter();
  const supabaseClient = useSupabaseClient();
  const [loading, setLoading] = useState(false);
  const { isLoading, subscription, userDetails } = useUser();

  const redirectToCustomerPortal = async () => {
    setLoading(true);
    try {
      const { url, error } = await postData({
        url: '/api/create-portal-link'
      });
      window.location.assign(url);
    } catch (error) {
      if (error) return alert((error as Error).message);
    }
    setLoading(false);
  };

  const subscriptionPrice =
    subscription &&
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: subscription?.prices?.currency,
      minimumFractionDigits: 0
    }).format((subscription?.prices?.unit_amount || 0) / 100);

  if (!userDetails) return null;

  return (
    <>
      <Navbar user={user} />
      <div className="m-8 flex flex-col justify-center items-center">
        <Box className="flex flex-col gap-6 w-5/6 md:w-3/4 xl:w-1/2">
          <AccountForm user={user} userDetails={userDetails} />
          <Divider></Divider>
          <div className="flex flex-col justify-center gap-8">
            <Heading>Subscription Details</Heading>
            <Text>
              {subscription
                ? `You are currently on the ${subscription?.prices?.products?.name} plan.`
                : "You're not subscribed!"}
            </Text>
            {subscription ? (
              <Text>
                {`You have ${subscription?.credits ? subscription?.credits : 0}
                ${subscription?.credits === 1 ? 'summary' : 'summaries'} with ${
                  subscription?.max_audio_length
                    ? subscription?.max_audio_length
                    : 0
                } minutes limit left in this period.`}
              </Text>
            ) : null}
            {subscription ? (
              <Accordion allowToggle>
                <AccordionItem>
                  <h2>
                    <AccordionButton>
                      <Box as="span" flex="1" textAlign="left">
                        How do I upgrage or cancel my subscription?
                      </Box>
                      <AccordionIcon />
                    </AccordionButton>
                  </h2>
                  <AccordionPanel pb={4} className="flex gap-2 flex-col">
                    <p>
                      To cancel your subscription, click the "Manage your
                      subscription" below and choose "Cancel plan" option.
                    </p>
                    <p>
                      {' '}
                      If you want to upgrade your subscription, first cancel
                      your current plan following the steps above and then
                      choose the plan you want to upgrade to.
                    </p>
                  </AccordionPanel>
                </AccordionItem>
              </Accordion>
            ) : null}
            <Button
              isLoading={loading}
              disabled={loading || !subscription}
              onClick={
                subscription ? redirectToCustomerPortal : () => router.push('/')
              }
            >
              {subscription ? 'Manage your subscription' : 'Subscribe'}
            </Button>
          </div>
          <Divider></Divider>
          <div className="flex justify-center">
            <Button
              colorScheme={'red'}
              onClick={async () => {
                await supabaseClient.auth.signOut();
                router.push('/');
              }}
            >
              Sign out
            </Button>
          </div>
        </Box>
      </div>
    </>
  );
}
