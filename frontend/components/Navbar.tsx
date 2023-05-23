import NextLink from 'next/link';
import { Link, Button, Box, Heading } from '@chakra-ui/react';
import { User } from '@supabase/auth-helpers-nextjs';
import { Subscription } from 'types';

interface Props {
  user: User;
}

export default function Navbar({ user }: Props) {
  return (
    <Box
      className="px-10 h-[80px] flex justify-between items-center flex-row py-4l"
      shadow={'md'}
    >
      <div className="flex gap-10 items-center">
        <Heading as={NextLink} href="/">
          Scribe
        </Heading>
        {user ? null : (
          <Link as={NextLink} href="#pricing" className="hidden sm:block">
            Pricing
          </Link>
        )}
      </div>
      {user ? (
        <Link as={NextLink} href="/account">
          Account
        </Link>
      ) : (
        <Button
          bgGradient={'linear(to-r, #7928CA, #FF0080)'}
          padding={'6px 20px'}
          rounded={'full'}
          href="/signin"
          as={NextLink}
          textColor="white"
          _hover={{
            bgGradient: 'linear(to-r, #7928CA, #FF0080)',
            opacity: 0.8
          }}
        >
          Sign in
        </Button>
      )}
    </Box>
  );
}
