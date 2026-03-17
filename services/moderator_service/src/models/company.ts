import { prisma } from "../config/prismaClient";
import { Company } from "../types/types";



export async function upsertCompany(company: Company, userId: string) {
    const existingCompany = await prisma.company.findUnique({
        where: { id: company.id },
    });

    const data = {
        title: company.title,
        description: company.description,
        verified: company.verified,
        business_type: company.business_type,
        industry_type: company.industry_type,
        send_customer_emails: company.send_customer_emails,
        updated_at: new Date(company.updated_at),
        member_count: company.member_count,
        route: company.route,
        logo_url: company.logo_url,
        user_id: userId,
    };

    if (existingCompany) {
        await prisma.company.update({
            where: { id: company.id },
            data: data,
        });
    } else {
        await prisma.company.create({
            data: {
                id: company.id,
                created_at: new Date(company.created_at),
                ...data
            },
        });
    }
}