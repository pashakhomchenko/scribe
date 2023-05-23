import {
  createBrowserSupabaseClient,
  User
} from '@supabase/auth-helpers-nextjs';

import { ProductWithPrice } from 'types';
import type { Database } from 'types_db';

export const supabase = createBrowserSupabaseClient<Database>();

export const getActiveProductsWithPrices = async (): Promise<
  ProductWithPrice[]
> => {
  const { data, error } = await supabase
    .from('products')
    .select('*, prices(*)')
    .eq('active', true)
    .eq('prices.active', true)
    .order('metadata->index')
    .order('unit_amount', { foreignTable: 'prices' });

  if (error) {
    console.log(error.message);
  }
  // TODO: improve the typing here.
  return (data as any) || [];
};

export const updateUserName = async (user: User, name: string) => {
  const { data, error } = await supabase
    .from('users')
    .update({
      full_name: name
    })
    .eq('id', user.id);
  if (error) {
    throw error;
  }
};

export const updateUserEmail = async (email: string) => {
  const { data, error } = await supabase.auth.updateUser({
    email: email
  });
  if (error) {
    throw error;
  }
};

export const updateUserPassword = async (password: string) => {
  const { data, error } = await supabase.auth.updateUser({
    password: password
  });
  if (error) {
    throw error;
  }
};
