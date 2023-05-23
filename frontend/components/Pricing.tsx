import { useState } from 'react';
import { useRouter } from 'next/router';

import { postData } from '@/utils/helpers';
import { getStripe } from '@/utils/stripe-client';
import { useUser } from '@/utils/useUser';

import { Price, ProductWithPrice } from 'types';
import {
  Heading,
  Text,
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  Stack,
  Divider,
  Button,
  ButtonGroup,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel
} from '@chakra-ui/react';

interface Props {
  products: ProductWithPrice[];
}

type BillingInterval = 'year' | 'month';

export default function Pricing({ products }: Props) {
  const router = useRouter();
  const [billingInterval, setBillingInterval] =
    useState<BillingInterval>('year');
  const [priceIdLoading, setPriceIdLoading] = useState<string>();
  const { user, isLoading, subscription } = useUser();

  const handleCheckout = async (price: Price) => {
    setPriceIdLoading(price.id);
    if (!user) {
      return router.push('/signin');
    }
    if (subscription) {
      return router.push('/account');
    }

    try {
      const { sessionId } = await postData({
        url: '/api/create-checkout-session',
        data: { price }
      });

      const stripe = await getStripe();
      stripe?.redirectToCheckout({ sessionId });
    } catch (error) {
      return alert((error as Error)?.message);
    } finally {
      setPriceIdLoading(undefined);
    }
  };

  if (!products.length)
    return (
      <section className="bg-black">
        <div className="max-w-6xl mx-auto py-8 sm:py-24 px-4 sm:px-6 lg:px-8">
          <div className="sm:flex sm:flex-col sm:align-center"></div>
          <p className="text-6xl font-extrabold text-white sm:text-center sm:text-6xl">
            No subscription pricing plans found. Create them in your{' '}
            <a
              className="text-pink-500 underline"
              href="https://dashboard.stripe.com/products"
              rel="noopener noreferrer"
              target="_blank"
            >
              Stripe Dashboard
            </a>
            .
          </p>
        </div>
      </section>
    );

  return (
    <section className="px-6 py-20" id="pricing">
      <div className="flex flex-col sm:align-center justify-center">
        <Heading size={'2xl'} textAlign={'center'}>
          Pricing Plans
        </Heading>
        <Text
          textAlign={'center'}
          className="mt-5 text-xl sm:text-center sm:text-2xl max-w-2xl m-auto"
        >
          {user
            ? 'You need to subscribe to get access to Scribe.'
            : 'Get intelligent summaries for your meetings right in your inbox.'}
        </Text>
        <Tabs
          variant="soft-rounded"
          colorScheme="green"
          className="self-center mt-6"
        >
          <TabList>
            <Tab onClick={() => setBillingInterval('year')}>Yearly billing</Tab>
            <Tab onClick={() => setBillingInterval('month')}>
              Monthly billing
            </Tab>
          </TabList>
        </Tabs>
      </div>
      <div className="mt-12 space-y-4 md:mt-16 md:space-y-0 md:grid md:grid-cols-3 sm:gap-6 lg:max-w-4xl lg:mx-auto">
        {products.map((product) => {
          const price = product?.prices?.find(
            (price) => price.interval === billingInterval
          );
          if (!price) return null;
          const priceString = new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: price.currency,
            minimumFractionDigits: 0
          }).format(
            billingInterval === 'month'
              ? (price?.unit_amount || 0) / 100
              : (price?.unit_amount || 0) / 100 / 12
          );
          return (
            <Card maxW="3xl" key={product.id}>
              <CardBody>
                <Stack mt="3" spacing="3">
                  <Heading size="md">{product.name}</Heading>
                  <Text>{product.description}</Text>
                  <div>
                    <span className="text-5xl font-extrabold white">
                      {priceString}
                    </span>
                    <span className="text-base font-medium">/month</span>
                  </div>
                </Stack>
              </CardBody>
              <CardFooter>
                <Button
                  disabled={isLoading}
                  isLoading={priceIdLoading === price.id}
                  onClick={() => handleCheckout(price)}
                  width={'full'}
                  rounded={'full'}
                  bg={'black'}
                  color={'white'}
                  border={'1px'}
                  borderColor={'black'}
                  _hover={{
                    bg: 'white',
                    color: 'black'
                  }}
                >
                  Subscribe
                </Button>
              </CardFooter>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
