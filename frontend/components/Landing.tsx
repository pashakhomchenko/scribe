import { Heading, Text, Box, Button } from '@chakra-ui/react';
import { ArrowDownIcon } from '@chakra-ui/icons';
import NextLink from 'next/link';
import Footer from '@/components/Footer';
import { User } from '@supabase/auth-helpers-nextjs';
import Pricing from '@/components/Pricing';

import { ProductWithPrice } from 'types';
import Banner from './Banner';

export default function Landing({
  user,
  products
}: {
  user: User;
  products: ProductWithPrice[];
}) {
  return (
    <>
      <section className="flex flex-col items-center justify-center px-6 height-screen-helper">
        <Banner />
        <Button
          bgGradient={'linear(to-r, #7928CA, #FF0080)'}
          padding={'10px 40px'}
          rounded={'full'}
          href="/signin"
          as={NextLink}
          textColor="white"
          _hover={{
            bgGradient: 'linear(to-r, #7928CA, #FF0080)',
            opacity: 0.8
          }}
        >
          {user ? 'Go to the app' : 'Get your summary now'}
        </Button>
      </section>
      <div>
        <Pricing products={products} />
      </div>
    </>
  );
}
