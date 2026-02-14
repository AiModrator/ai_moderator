import Whop from "@whop/sdk";


export const clientWhop = new Whop({
  apiKey: process.env.WHOP_API_KEY,
});


export const testClient =  new Whop({
  apiKey: process.env.WHOP_API_KEY,
  baseURL:"https://sandbox-api.whop.com/api/v1" 
});






