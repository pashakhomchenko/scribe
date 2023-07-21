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
      <section className="flex flex-col gap-12 items-center justify-center px-10 py-6">
        <Heading as="h2" size="2xl" textAlign="center">
          How does it work?
        </Heading>
        <div className="flex items-center justify-center">
          <video width="1920" height="1080" controls>
            <source src="/demo.mp4" type="video/mp4" />
            Your browser does not support video.
          </video>
        </div>
      </section>
      <div>
        <Pricing products={products} />
      </div>
    </>
  );
}
